from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.db.models import Prefetch, Q, QuerySet, Sum
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import NinjaAPI, Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth
from pydantic import Field

from .models import (
    Campaign,
    Character,
    ExperienceEntry,
    ExperienceTransaction,
    InventoryEntry,
    InventoryItem,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
    Player,
)
from .services import exchange_coins, reverse_transaction
from .services.ledger import post_inventory_transaction, post_money_transaction


class Credentials(Schema):
    username: str
    password: str


class EquipmentMetadata(Schema):
    category: str | None = None
    source_book: str | None = None
    item_type: str | None = None
    cost_amount: Decimal | None = None
    cost_currency: str | None = None
    weight_amount: Decimal | None = None
    weight_unit: str | None = None
    rarity: str | None = None
    is_magic: bool | None = None
    requires_attunement: bool | None = None


class ItemCreate(Schema):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: str = ""
    metadata: EquipmentMetadata | None = None


class ItemUpdate(Schema):
    name: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    description: str | None = None
    metadata: EquipmentMetadata | None = None


class InventoryTransactionCreate(Schema):
    from_character_id: int | None
    to_character_id: int | None
    item_id: int
    quantity: int
    description: str = ""


class MoneyTransferCreate(Schema):
    from_character_id: int | None
    to_character_id: int | None
    amounts: dict[str, int]
    description: str = ""


class MoneyExchangeCreate(Schema):
    character_id: int
    given: dict[str, int]
    received: dict[str, int]
    description: str = ""


class SharedXpAwardCreate(Schema):
    amount: int
    description: str = ""


class MemberCreate(Schema):
    username: str
    is_game_master: bool = False


class MemberUpdate(Schema):
    is_game_master: bool


class CharacterCreate(Schema):
    name: str
    race: str
    character_class: str
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    player_id: int | None = None


class CharacterUpdate(Schema):
    name: str | None = None
    race: str | None = None
    character_class: str | None = None
    strength: int | None = None
    dexterity: int | None = None
    constitution: int | None = None
    intelligence: int | None = None
    wisdom: int | None = None
    charisma: int | None = None
    is_active: bool | None = None
    is_archived: bool | None = None
    player_id: int | None = None


api = NinjaAPI(title="Hoard API", version="1.0.0", auth=django_auth)
campaigns = Router(tags=["campaigns"], auth=django_auth)


def _unprocessable(error: DjangoValidationError) -> HttpError:
    messages = error.message_dict if hasattr(error, "message_dict") else error.messages
    return HttpError(422, str(messages))


def _metadata_values(
    data: EquipmentMetadata | None,
    *,
    defaults: InventoryItem | None = None,
    partial: bool = False,
) -> dict[str, object]:
    supplied = data.model_dump(exclude_unset=True) if data else {}
    if partial and data is None:
        return {}

    def text(name: str, default: str = "") -> str:
        value = supplied.get(name, default)
        return "" if value is None else value.strip()

    values = {
        "equipment_category": text(
            "category", defaults.equipment_category if defaults else ""
        ),
        "source_book": text("source_book", defaults.source_book if defaults else ""),
        "item_type": text("item_type", defaults.item_type if defaults else ""),
        "cost_amount": supplied.get(
            "cost_amount", defaults.cost_amount if defaults else None
        ),
        "cost_currency": text(
            "cost_currency", defaults.cost_currency if defaults else ""
        ),
        "weight_amount": supplied.get(
            "weight_amount", defaults.weight_amount if defaults else None
        ),
        "weight_unit": text("weight_unit", defaults.weight_unit if defaults else ""),
        "rarity": text("rarity", defaults.rarity if defaults else ""),
        "is_magic": supplied.get("is_magic", defaults.is_magic if defaults else None),
        "requires_attunement": supplied.get(
            "requires_attunement", defaults.requires_attunement if defaults else None
        ),
    }
    if values["cost_currency"] and values["cost_currency"] not in {
        "cp",
        "sp",
        "ep",
        "gp",
        "pp",
    }:
        raise HttpError(422, "metadata.cost_currency must be cp, sp, ep, gp, or pp.")
    if (values["cost_amount"] is None) == bool(values["cost_currency"]):
        raise HttpError(422, "Cost amount and currency must be supplied together.")
    if (values["weight_amount"] is None) == bool(values["weight_unit"]):
        raise HttpError(422, "Weight amount and unit must be supplied together.")
    return values


def _campaign_access(request, campaign_id: int) -> tuple[Campaign, Player]:
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    try:
        return campaign, Player.objects.get(
            campaign=campaign, user=request.auth, is_active=True
        )
    except Player.DoesNotExist as error:
        raise HttpError(403, "You are not a member of this campaign.") from error


def _game_master(player: Player) -> None:
    if not player.is_game_master:
        raise HttpError(403, "This action requires a campaign game master.")


def _character(campaign: Campaign, character_id: int | None) -> Character:
    if character_id is None:
        raise HttpError(422, "A character id is required.")
    return get_object_or_404(Character, pk=character_id, campaign=campaign)


def _items(
    campaign: Campaign, *, include_disabled_sources: bool = False
) -> QuerySet[InventoryItem]:
    items = InventoryItem.objects.filter(
        Q(campaign=campaign) | Q(campaign__isnull=True)
    ).select_related("created_by__user")
    return (
        items
        if include_disabled_sources
        else items.filter(
            Q(campaign=campaign)
            | Q(campaign__isnull=True, source_system__in=campaign.item_sources)
        )
    )


def _item(
    campaign: Campaign, item_id: int, *, include_disabled_sources: bool = False
) -> InventoryItem:
    return get_object_or_404(
        _items(campaign, include_disabled_sources=include_disabled_sources), pk=item_id
    )


def _item_data(item: InventoryItem) -> dict[str, object]:
    return {
        "id": item.pk,
        "name": item.name,
        "description": item.description,
        "campaign_id": item.campaign_id,
        "created_by_id": item.created_by_id,
        "created_by_username": item.created_by.user.get_username()
        if item.created_by_id
        else None,
        "source_system": item.source_system or None,
        "source_identifier": item.source_identifier or None,
        "source_repository": item.source_repository or None,
        "equipment": {
            "category": item.equipment_category or None,
            "source_book": item.source_book or None,
            "item_type": item.item_type or None,
            "cost_amount": str(item.cost_amount)
            if item.cost_amount is not None
            else None,
            "cost_currency": item.cost_currency or None,
            "weight_amount": str(item.weight_amount)
            if item.weight_amount is not None
            else None,
            "weight_unit": item.weight_unit or None,
            "rarity": item.rarity or None,
            "is_magic": item.is_magic,
            "requires_attunement": item.requires_attunement,
        },
        "is_imported": item.is_imported,
    }


def _transaction_data(
    transaction: InventoryTransaction | MoneyTransaction | ExperienceTransaction,
) -> dict[str, object]:
    return {
        "id": transaction.pk,
        "ledger": transaction._meta.model_name.removesuffix("transaction"),
        "description": transaction.description,
        "created_at": transaction.created_at,
        "created_by_id": transaction.created_by_id,
    }


def _money_data(character: Character) -> dict[str, int | str]:
    return {
        "cp": character.money.copper,
        "sp": character.money.silver,
        "ep": character.money.electrum,
        "gp": character.money.gold,
        "pp": character.money.platinum,
        "gold_value": str(character.money.gold_value),
    }


def _party_money(campaign: Campaign) -> dict[str, int | str]:
    totals = {key: 0 for key in ("cp", "sp", "ep", "gp", "pp")}
    rows = (
        MoneyEntry.objects.filter(
            account__character__campaign=campaign,
            account__character__is_active=True,
            account__character__is_archived=False,
            account__character__player__isnull=False,
        )
        .values("denomination")
        .annotate(total=Sum("amount"))
    )
    for row in rows:
        totals[row["denomination"]] = row["total"]
    totals["gold_value"] = str(
        Decimal(totals["cp"]) / 100
        + Decimal(totals["sp"]) / 10
        + Decimal(totals["ep"]) / 2
        + Decimal(totals["gp"])
        + Decimal(totals["pp"]) * 10
    )
    return totals


def _character_data(character: Character) -> dict[str, object]:
    return {
        "id": character.pk,
        "name": character.name,
        "is_player_character": bool(character.player_id),
        "is_active": character.is_active,
        "is_archived": character.is_archived,
        "archived_at": character.archived_at,
        "race": character.race,
        "class": character.character_class,
        "strength": character.strength,
        "dexterity": character.dexterity,
        "constitution": character.constitution,
        "intelligence": character.intelligence,
        "wisdom": character.wisdom,
        "charisma": character.charisma,
        "experience": character.experience,
        "money": _money_data(character),
        "inventory": [
            {"item_id": item.pk, "name": item.name, "quantity": quantity}
            for item, quantity in character.inventory.items()
        ],
    }


@api.get("/auth/csrf/", auth=None)
@ensure_csrf_cookie
@csrf_exempt
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@api.get("/auth/session/")
def session(request):
    return {"id": request.auth.pk, "username": request.auth.get_username()}


@api.post("/auth/session/", auth=None)
def create_session(request, payload: Credentials):
    failure = CsrfViewMiddleware(lambda _: None).process_view(
        request, create_session, (), {}
    )
    if failure is not None:
        return failure
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid username or password.")
    login(request, user)
    return {"id": user.pk, "username": user.get_username()}


@api.delete("/auth/session/", response={204: None})
def delete_session(request):
    logout(request)
    return 204, None


@campaigns.get("/")
def campaign_list(request):
    return [
        {
            "id": m.campaign_id,
            "name": m.campaign.name,
            "is_game_master": m.is_game_master,
        }
        for m in Player.objects.filter(user=request.auth, is_active=True)
        .select_related("campaign")
        .order_by("campaign__name")
    ]


@campaigns.get("/{campaign_id}/")
def campaign_detail(request, campaign_id: int):
    campaign, player = _campaign_access(request, campaign_id)
    visible = Q(is_active=True, is_archived=False, player__isnull=False) | Q(
        player=player
    )
    characters = (
        campaign.characters.all()
        if player.is_game_master
        else campaign.characters.filter(visible)
    )
    return {
        "id": campaign.pk,
        "name": campaign.name,
        "use_shared_exp": campaign.use_shared_exp,
        "shared_experience": campaign.shared_experience,
        "is_game_master": player.is_game_master,
        "item_sources": campaign.item_sources,
        "party_money": _party_money(campaign),
        "characters": [_character_data(c) for c in characters],
    }


@campaigns.get("/{campaign_id}/members/")
def member_list(request, campaign_id: int):
    campaign, _ = _campaign_access(request, campaign_id)
    return [
        {
            "id": member.pk,
            "username": member.user.get_username(),
            "is_game_master": member.is_game_master,
            "is_active": member.is_active,
        }
        for member in campaign.players.select_related("user")
    ]


@campaigns.post("/{campaign_id}/members/", response={201: dict})
def member_create(request, campaign_id: int, payload: MemberCreate):
    campaign, player = _campaign_access(request, campaign_id)
    _game_master(player)
    user = get_object_or_404(get_user_model(), username=payload.username)
    member, created = Player.objects.get_or_create(
        campaign=campaign,
        user=user,
        defaults={"is_game_master": payload.is_game_master},
    )
    if not created:
        raise HttpError(409, "That user already has a campaign membership.")
    return 201, {
        "id": member.pk,
        "username": member.user.get_username(),
        "is_game_master": member.is_game_master,
        "is_active": member.is_active,
    }


@campaigns.patch("/{campaign_id}/members/{member_id}/")
def member_update(request, campaign_id: int, member_id: int, payload: MemberUpdate):
    campaign, player = _campaign_access(request, campaign_id)
    _game_master(player)
    member = get_object_or_404(Player, pk=member_id, campaign=campaign)
    member.is_game_master = payload.is_game_master
    member.save(update_fields=("is_game_master",))
    return {
        "id": member.pk,
        "username": member.user.get_username(),
        "is_game_master": member.is_game_master,
        "is_active": member.is_active,
    }


@campaigns.delete("/{campaign_id}/members/{member_id}/", response={204: None})
def member_delete(request, campaign_id: int, member_id: int):
    campaign, player = _campaign_access(request, campaign_id)
    _game_master(player)
    member = get_object_or_404(Player, pk=member_id, campaign=campaign, is_active=True)
    with db_transaction.atomic():
        member.is_active = False
        member.save(update_fields=("is_active",))
        member.characters.filter(is_archived=False).update(
            is_archived=True, is_active=False, archived_at=timezone.now()
        )
    return 204, None


@campaigns.get("/{campaign_id}/characters/")
def character_list(request, campaign_id: int):
    campaign, player = _campaign_access(request, campaign_id)
    queryset = (
        campaign.characters.all()
        if player.is_game_master
        else campaign.characters.filter(
            Q(is_active=True, is_archived=False, player__isnull=False)
            | Q(player=player)
        )
    )
    return [_character_data(character) for character in queryset]


@campaigns.get("/{campaign_id}/characters/me/")
def my_characters(request, campaign_id: int):
    campaign, player = _campaign_access(request, campaign_id)
    return [
        _character_data(character)
        for character in campaign.characters.filter(player=player)
    ]


@campaigns.post("/{campaign_id}/characters/", response={201: dict})
def character_create(request, campaign_id: int, payload: CharacterCreate):
    campaign, actor = _campaign_access(request, campaign_id)
    owner = actor
    if actor.is_game_master and "player_id" in payload.model_fields_set:
        owner = (
            get_object_or_404(
                Player, pk=payload.player_id, campaign=campaign, is_active=True
            )
            if payload.player_id
            else None
        )
    character = Character(
        campaign=campaign,
        player=owner,
        is_active=False,
        name=payload.name,
        race=payload.race,
        character_class=payload.character_class,
        strength=payload.strength,
        dexterity=payload.dexterity,
        constitution=payload.constitution,
        intelligence=payload.intelligence,
        wisdom=payload.wisdom,
        charisma=payload.charisma,
    )
    try:
        character.full_clean()
        character.save()
        if owner is not None:
            character.activate()
        else:
            character.is_active = True
            character.save(update_fields=("is_active",))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _character_data(character)


def _editable_character(
    request, campaign_id: int, character_id: int
) -> tuple[Character, Player]:
    campaign, actor = _campaign_access(request, campaign_id)
    character = get_object_or_404(Character, pk=character_id, campaign=campaign)
    if not actor.is_game_master and character.player_id != actor.pk:
        raise HttpError(403, "You may only manage your own character.")
    return character, actor


@campaigns.get("/{campaign_id}/characters/{character_id}/")
def character_detail(request, campaign_id: int, character_id: int):
    campaign, actor = _campaign_access(request, campaign_id)
    character = get_object_or_404(Character, pk=character_id, campaign=campaign)
    if (
        not actor.is_game_master
        and character.player_id != actor.pk
        and not (
            character.is_active and not character.is_archived and character.player_id
        )
    ):
        raise HttpError(404, "Character not found.")
    return _character_data(character)


@campaigns.patch("/{campaign_id}/characters/{character_id}/")
def character_update(
    request, campaign_id: int, character_id: int, payload: CharacterUpdate
):
    staff_only_fields = {"player_id", "is_archived"}
    if request.auth.is_staff and payload.model_fields_set <= staff_only_fields:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        character = get_object_or_404(Character, pk=character_id, campaign=campaign)
        actor = None
    else:
        character, actor = _editable_character(request, campaign_id, character_id)
    if "player_id" in payload.model_fields_set:
        if not request.auth.is_staff:
            raise HttpError(403, "Only staff may reassign characters.")
        character.player = (
            get_object_or_404(Player, pk=payload.player_id, campaign_id=campaign_id)
            if payload.player_id
            else None
        )
    if "is_archived" in payload.model_fields_set:
        if not request.auth.is_staff:
            raise HttpError(403, "Only staff may restore archived characters.")
        character.is_archived = bool(payload.is_archived)
        character.archived_at = (
            None
            if not character.is_archived
            else character.archived_at or timezone.now()
        )
        if character.is_archived:
            character.is_active = False
    for field in (
        "name",
        "race",
        "character_class",
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    ):
        if field in payload.model_fields_set:
            setattr(character, field, getattr(payload, field))
    if "is_active" in payload.model_fields_set:
        if payload.is_active and character.is_archived:
            raise HttpError(
                409, "Archived characters must be restored by staff before activation."
            )
        if payload.is_active and not character.is_active:
            character.is_active = False
            character.save()
            character.activate()
        else:
            character.is_active = bool(payload.is_active)
    try:
        character.full_clean()
        character.save()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return _character_data(character)


@campaigns.delete("/{campaign_id}/characters/{character_id}/")
def character_delete(request, campaign_id: int, character_id: int):
    character, _ = _editable_character(request, campaign_id, character_id)
    character.is_archived, character.is_active, character.archived_at = (
        True,
        False,
        timezone.now(),
    )
    character.save(update_fields=("is_archived", "is_active", "archived_at"))
    return _character_data(character)


@campaigns.get("/{campaign_id}/items/")
def item_list(request, campaign_id: int):
    campaign, _ = _campaign_access(request, campaign_id)
    return [_item_data(item) for item in _items(campaign).order_by("name")]


@campaigns.post("/{campaign_id}/items/", response={201: dict})
def item_create(request, campaign_id: int, payload: ItemCreate):
    campaign, player = _campaign_access(request, campaign_id)
    item = InventoryItem(
        campaign=campaign,
        created_by=player,
        name=payload.name.strip(),
        description=payload.description,
        **_metadata_values(payload.metadata),
    )
    try:
        item.full_clean()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    item.save()
    return 201, _item_data(item)


@campaigns.get("/{campaign_id}/items/{item_id}/")
def item_detail(request, campaign_id: int, item_id: int):
    campaign, _ = _campaign_access(request, campaign_id)
    return _item_data(_item(campaign, item_id))


def _editable_item(request, campaign_id: int, item_id: int) -> InventoryItem:
    campaign, player = _campaign_access(request, campaign_id)
    item = _item(campaign, item_id)
    if item.campaign_id is None:
        raise HttpError(403, "Imported catalogue items are read-only.")
    if not player.is_game_master:
        raise HttpError(403, "Only a game master may edit this item.")
    return item


@campaigns.patch("/{campaign_id}/items/{item_id}/")
def item_update(request, campaign_id: int, item_id: int, payload: ItemUpdate):
    item = _editable_item(request, campaign_id, item_id)
    if "name" in payload.model_fields_set:
        item.name = payload.name.strip()  # type: ignore[union-attr]
    if "description" in payload.model_fields_set:
        item.description = payload.description  # type: ignore[assignment]
    if "metadata" in payload.model_fields_set:
        for name, value in _metadata_values(payload.metadata, defaults=item).items():
            setattr(item, name, value)
    try:
        item.full_clean()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    item.save()
    return _item_data(item)


@campaigns.delete("/{campaign_id}/items/{item_id}/", response={204: None})
def item_delete(request, campaign_id: int, item_id: int):
    item = _editable_item(request, campaign_id, item_id)
    if item.entries.exists():
        raise HttpError(409, "Items referenced by ledger entries cannot be deleted.")
    item.delete()
    return 204, None


@campaigns.post("/{campaign_id}/inventory-transactions/", response={201: dict})
def inventory_transaction_create(
    request, campaign_id: int, payload: InventoryTransactionCreate
):
    campaign, player = _campaign_access(request, campaign_id)
    if payload.from_character_id is None and payload.to_character_id is None:
        raise HttpError(
            422, "An inventory transaction needs a source or destination character."
        )
    source = (
        _character(campaign, payload.from_character_id)
        if payload.from_character_id
        else None
    )
    destination = (
        _character(campaign, payload.to_character_id)
        if payload.to_character_id
        else None
    )
    if (
        not player.is_game_master
        and source is not None
        and source.player_id != player.pk
    ):
        raise HttpError(
            403, "Players may only transfer inventory from their own character."
        )
    item = _item(
        campaign, payload.item_id, include_disabled_sources=destination is None
    )
    if source is not None and source.inventory.get(item, 0) < payload.quantity:
        raise HttpError(
            422, "A character cannot transfer more of an item than they hold."
        )
    try:
        transaction = post_inventory_transaction(
            from_account=source.inventory_account()
            if source
            else campaign.inventory_system_account(),
            to_account=destination.inventory_account()
            if destination
            else campaign.inventory_system_account(),
            item=item,
            quantity=payload.quantity,
            description=payload.description,
        )
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    transaction.created_by = player
    transaction.save(update_fields=("created_by",))
    return 201, _transaction_data(transaction)


def _coin_amounts(amounts: dict[str, int]) -> dict[MoneyEntry.Denomination, int]:
    result: dict[MoneyEntry.Denomination, int] = {}
    for denomination, amount in amounts.items():
        try:
            key = MoneyEntry.Denomination(denomination)
        except ValueError as error:
            raise HttpError(422, "Unknown currency denomination.") from error
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise HttpError(422, "Coin amounts must be positive integers.")
        result[key] = amount
    if not result:
        raise HttpError(422, "At least one coin amount is required.")
    return result


@campaigns.post("/{campaign_id}/money-transfers/", response={201: dict})
def money_transfer_create(request, campaign_id: int, payload: MoneyTransferCreate):
    campaign, player = _campaign_access(request, campaign_id)
    if payload.from_character_id is None and payload.to_character_id is None:
        raise HttpError(
            422, "A money transfer needs a source or destination character."
        )
    source = (
        _character(campaign, payload.from_character_id)
        if payload.from_character_id
        else None
    )
    destination = (
        _character(campaign, payload.to_character_id)
        if payload.to_character_id
        else None
    )
    if not player.is_game_master and (source is None or source.player_id != player.pk):
        raise HttpError(
            403, "Players may only transfer money from their own character."
        )
    amounts = _coin_amounts(payload.amounts)
    if source is not None:
        balances = {
            MoneyEntry.Denomination.COPPER: source.money.copper,
            MoneyEntry.Denomination.SILVER: source.money.silver,
            MoneyEntry.Denomination.ELECTRUM: source.money.electrum,
            MoneyEntry.Denomination.GOLD: source.money.gold,
            MoneyEntry.Denomination.PLATINUM: source.money.platinum,
        }
        if any(
            amount > balances[denomination] for denomination, amount in amounts.items()
        ):
            raise HttpError(
                422, "A character cannot transfer more coins than they hold."
            )
    try:
        transaction = post_money_transaction(
            [
                (
                    source.money_account()
                    if source
                    else campaign.money_system_account(),
                    denomination,
                    -amount,
                )
                for denomination, amount in amounts.items()
            ]
            + [
                (
                    destination.money_account()
                    if destination
                    else campaign.money_system_account(),
                    denomination,
                    amount,
                )
                for denomination, amount in amounts.items()
            ],
            description=payload.description,
        )
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    transaction.created_by = player
    transaction.save(update_fields=("created_by",))
    return 201, _transaction_data(transaction)


@campaigns.post("/{campaign_id}/money-exchanges/", response={201: dict})
def money_exchange_create(request, campaign_id: int, payload: MoneyExchangeCreate):
    campaign, player = _campaign_access(request, campaign_id)
    character = _character(campaign, payload.character_id)
    if not player.is_game_master and character.player_id != player.pk:
        raise HttpError(403, "Players may only exchange their own coins.")
    try:
        transaction = exchange_coins(
            character=character,
            given=_coin_amounts(payload.given),
            received=_coin_amounts(payload.received),
            description=payload.description,
        )
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    transaction.created_by = player
    transaction.save(update_fields=("created_by",))
    return 201, _transaction_data(transaction)


@campaigns.post("/{campaign_id}/shared-xp-awards/", response={201: dict})
def shared_xp_award_create(request, campaign_id: int, payload: SharedXpAwardCreate):
    campaign, player = _campaign_access(request, campaign_id)
    _game_master(player)
    try:
        _, transaction = campaign.award_shared_experience(
            payload.amount,
            description=payload.description,
            created_by=player,
            return_transaction=True,
        )
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _transaction_data(transaction)


def _entry_data(
    entry: InventoryEntry | MoneyEntry | ExperienceEntry,
) -> dict[str, object]:
    ledger = entry.transaction._meta.model_name.removesuffix("transaction")
    data: dict[str, object] = {
        "account_id": entry.account_id,
        "account_name": f"Campaign {ledger} system"
        if entry.account.is_system
        else entry.account.character.name,
        "is_system_account": entry.account.is_system,
        "amount": entry.amount,
    }
    if isinstance(entry, InventoryEntry):
        data.update(item_id=entry.item_id, item_name=entry.item.name)
    elif isinstance(entry, MoneyEntry):
        data["denomination"] = entry.denomination
    return data


def _history_data(
    transaction: InventoryTransaction | MoneyTransaction | ExperienceTransaction,
) -> dict[str, object]:
    data = _transaction_data(transaction)
    data.update(
        entries=[_entry_data(entry) for entry in transaction.entries.all()],
        reversal_of_id=transaction.reversal_of_id,
        is_reversed=type(transaction).objects.filter(reversal_of=transaction).exists(),
    )
    if isinstance(transaction, ExperienceTransaction):
        data.update(
            reason=transaction.reason,
            requested_amount=transaction.requested_amount,
            discarded_amount=transaction.discarded_amount,
        )
    return data


TRANSACTION_MODELS = {
    "inventory": InventoryTransaction,
    "money": MoneyTransaction,
    "experience": ExperienceTransaction,
}


def _transaction_queryset(model, campaign: Campaign):
    entry_model = model._meta.get_field("entries").related_model
    entries = (
        entry_model.objects.select_related("account__character", "item")
        if model is InventoryTransaction
        else entry_model.objects.select_related("account__character")
    )
    return model.objects.filter(campaign=campaign).prefetch_related(
        Prefetch("entries", queryset=entries)
    )


@campaigns.get("/{campaign_id}/transactions/")
def transaction_list(
    request,
    campaign_id: int,
    ledger: Literal["all", "inventory", "money", "experience"] = "all",
    page: int = 1,
    page_size: int = 25,
):
    campaign, player = _campaign_access(request, campaign_id)
    if page < 1 or not 1 <= page_size <= 100:
        raise HttpError(
            422, "page must be positive and page_size must be between 1 and 100."
        )
    models = (
        TRANSACTION_MODELS.items()
        if ledger == "all"
        else ((ledger, TRANSACTION_MODELS[ledger]),)
    )
    transactions = []
    for _, model in models:
        queryset = _transaction_queryset(model, campaign)
        if not player.is_game_master:
            queryset = queryset.filter(
                entries__account__character__player=player
            ).distinct()
        transactions.extend(queryset)
    transactions.sort(key=lambda transaction: transaction.created_at, reverse=True)
    start = (page - 1) * page_size
    return {
        "count": len(transactions),
        "page": page,
        "page_size": page_size,
        "results": [_history_data(t) for t in transactions[start : start + page_size]],
    }


@campaigns.get("/{campaign_id}/transactions/{ledger}/{transaction_id}/")
def transaction_detail(
    request,
    campaign_id: int,
    ledger: Literal["inventory", "money", "experience"],
    transaction_id: int,
):
    campaign, player = _campaign_access(request, campaign_id)
    transaction = get_object_or_404(
        _transaction_queryset(TRANSACTION_MODELS[ledger], campaign), pk=transaction_id
    )
    if (
        not player.is_game_master
        and not transaction.entries.filter(account__character__player=player).exists()
    ):
        raise HttpError(
            403, "You may only view transactions involving your characters."
        )
    if hasattr(transaction, "reversal"):
        raise HttpError(410, "This transaction has been reversed.")
    return _history_data(transaction)


@campaigns.delete("/{campaign_id}/transactions/{ledger}/{transaction_id}/")
def transaction_delete(
    request,
    campaign_id: int,
    ledger: Literal["inventory", "money", "experience"],
    transaction_id: int,
):
    campaign, player = _campaign_access(request, campaign_id)
    original = get_object_or_404(
        TRANSACTION_MODELS[ledger], pk=transaction_id, campaign=campaign
    )
    latest = (
        TRANSACTION_MODELS[ledger]
        .objects.filter(campaign=campaign)
        .order_by("-created_at", "-pk")
        .first()
    )
    if latest is None or latest.pk != original.pk:
        raise HttpError(
            409, "Only the latest transaction in this ledger may be reversed."
        )
    if hasattr(original, "reversal") or original.reversal_of_id:
        raise HttpError(409, "Reversal transactions are final.")
    if not player.is_game_master and original.created_by_id != player.pk:
        raise HttpError(
            403, "Only the initiator or a game master may reverse this transaction."
        )
    try:
        reversed_transaction = reverse_transaction(original)
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    reversed_transaction.created_by = player
    reversed_transaction.save(update_fields=("created_by",))
    return _history_data(reversed_transaction)


api.add_router("/campaigns", campaigns)
