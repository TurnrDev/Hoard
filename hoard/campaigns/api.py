from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Annotated, Literal

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.db.models import Prefetch, Q, Sum
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import File, NinjaAPI, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth
from pydantic import Field

from .models import (
    Campaign,
    CampaignContext,
    Character,
    ExperienceTransaction,
    InventoryEntry,
    InventoryItem,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
)
from .services import exchange_coins, reverse_transaction
from .services.cah import ABILITIES, SKILL_NAMES, parse_cah
from .services.ledger import post_inventory_transaction, post_money_transaction


class Credentials(Schema):
    username: str
    password: str


class ContextCreate(Schema):
    username: str
    kind: Literal["gm", "pc"]


class UserCreate(Schema):
    username: Annotated[str, Field(min_length=1, max_length=150)]
    email: str = ""


class CharacterCreate(Schema):
    name: str
    race: str = ""
    character_class: str = ""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    is_npc: bool = False


class CharacterUpdate(Schema):
    name: str | None = None
    race: str | None = None
    character_class: str | None = None
    base_hp: int | None = None
    proficiency_bonus_adjustment: int | None = None
    strength: int | None = None
    dexterity: int | None = None
    constitution: int | None = None
    intelligence: int | None = None
    wisdom: int | None = None
    charisma: int | None = None
    strength_modifier_adjustment: int | None = None
    dexterity_modifier_adjustment: int | None = None
    constitution_modifier_adjustment: int | None = None
    intelligence_modifier_adjustment: int | None = None
    wisdom_modifier_adjustment: int | None = None
    charisma_modifier_adjustment: int | None = None
    strength_save_proficient: bool | None = None
    dexterity_save_proficient: bool | None = None
    constitution_save_proficient: bool | None = None
    intelligence_save_proficient: bool | None = None
    wisdom_save_proficient: bool | None = None
    charisma_save_proficient: bool | None = None
    strength_save_adjustment: int | None = None
    dexterity_save_adjustment: int | None = None
    constitution_save_adjustment: int | None = None
    intelligence_save_adjustment: int | None = None
    wisdom_save_adjustment: int | None = None
    charisma_save_adjustment: int | None = None
    skill_proficiencies: (
        dict[str, Literal["none", "half", "proficient", "expertise"]] | None
    ) = None


class ItemCreate(Schema):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: str = ""


class ItemUpdate(Schema):
    name: str | None = None
    description: str | None = None


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


class CahCommit(Schema):
    token: str
    character_id: int | None = None


api = NinjaAPI(title="Hoard API", version="2.0.0", auth=django_auth)
contexts = Router(tags=["contexts"], auth=django_auth)

SKILL_ABILITIES = {
    "acrobatics": "dexterity",
    "animal_handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}
PASSWORD_WORDS = (
    "amber",
    "badger",
    "candle",
    "dawn",
    "elm",
    "falcon",
    "garden",
    "harbor",
    "ivory",
    "juniper",
    "kestrel",
    "lantern",
    "meadow",
    "north",
    "orbit",
    "pepper",
    "quartz",
    "raven",
    "summer",
    "thistle",
    "umber",
    "velvet",
    "willow",
    "xenon",
    "yarrow",
    "zephyr",
)


def _unprocessable(error: DjangoValidationError) -> HttpError:
    messages = error.message_dict if hasattr(error, "message_dict") else error.messages
    return HttpError(422, str(messages))


def _context_access(request, context_id: int) -> CampaignContext:
    return get_object_or_404(
        CampaignContext.objects.select_related("campaign", "user", "character"),
        pk=context_id,
        user=request.auth,
        is_active=True,
    )


def _gm(context: CampaignContext) -> None:
    if context.kind != CampaignContext.Kind.GM:
        raise HttpError(403, "This action requires a game-master context.")


def _character(context: CampaignContext, character_id: int | None) -> Character:
    if character_id is None:
        raise HttpError(422, "A character id is required.")
    return get_object_or_404(Character, pk=character_id, campaign=context.campaign)


def _is_owner(context: CampaignContext, character: Character) -> bool:
    return (
        character.context_id is not None
        and character.context.user_id == context.user_id
    )


def _visible_characters(context: CampaignContext):
    query = Q(is_active=True, is_archived=False, context__isnull=False)
    return (
        context.campaign.characters.all()
        if context.kind == CampaignContext.Kind.GM
        else context.campaign.characters.filter(query | Q(context__user=context.user))
    )


def _context_data(context: CampaignContext) -> dict[str, object]:
    character = getattr(context, "character", None)
    return {
        "id": context.pk,
        "campaign_id": context.campaign_id,
        "campaign_name": context.campaign.name,
        "kind": context.kind,
        "character_id": character.pk if character else None,
        "character_name": character.name if character else None,
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


def _sheet_data(character: Character) -> dict[str, object]:
    return {
        "level": character.level,
        "base_hp": character.base_hp,
        "max_hp": character.max_hp,
        "proficiency_bonus_adjustment": character.proficiency_bonus_adjustment,
        "proficiency_bonus": character.proficiency_bonus,
        "abilities": {
            ability: {
                "score": getattr(character, ability),
                "modifier": character.ability_modifier(ability),
                "adjustment": getattr(character, f"{ability}_modifier_adjustment"),
            }
            for ability in ABILITIES
        },
        "saves": {
            ability: {
                "proficient": getattr(character, f"{ability}_save_proficient"),
                "adjustment": getattr(character, f"{ability}_save_adjustment"),
                "bonus": character.saving_throw(ability),
            }
            for ability in ABILITIES
        },
        "skills": {
            skill: {
                "proficiency": character.skill_proficiencies.get(skill, "none"),
                "bonus": character.skill_bonus(skill, ability),
            }
            for skill, ability in SKILL_ABILITIES.items()
        },
    }


def _character_data(character: Character) -> dict[str, object]:
    return {
        "id": character.pk,
        "context_id": character.context_id,
        "name": character.name,
        "is_player_character": character.is_player_character,
        "is_active": character.is_active,
        "is_archived": character.is_archived,
        "archived_at": character.archived_at,
        "race": character.race,
        "class": character.character_class,
        "sheet": _sheet_data(character),
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


def _party_money(campaign: Campaign) -> dict[str, int | str]:
    totals = {key: 0 for key in ("cp", "sp", "ep", "gp", "pp")}
    rows = (
        MoneyEntry.objects.filter(
            account__character__campaign=campaign,
            account__character__is_active=True,
            account__character__is_archived=False,
            account__character__context__isnull=False,
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
            "cost_amount": (
                str(item.cost_amount) if item.cost_amount is not None else None
            ),
            "cost_currency": item.cost_currency or None,
            "weight_amount": (
                str(item.weight_amount) if item.weight_amount is not None else None
            ),
            "weight_unit": item.weight_unit or None,
            "rarity": item.rarity or None,
            "is_magic": item.is_magic,
            "requires_attunement": item.requires_attunement,
        },
        "is_imported": item.is_imported,
    }


def _items(campaign: Campaign):
    return (
        InventoryItem.objects.filter(Q(campaign=campaign) | Q(campaign__isnull=True))
        .filter(
            Q(campaign=campaign)
            | Q(campaign__isnull=True, source_system__in=campaign.item_sources)
        )
        .select_related("created_by__user")
    )


def _transaction_data(
    posted: InventoryTransaction | MoneyTransaction | ExperienceTransaction,
) -> dict[str, object]:
    return {
        "id": posted.pk,
        "ledger": posted._meta.model_name.removesuffix("transaction"),
        "description": posted.description,
        "created_at": posted.created_at,
        "created_by_id": posted.created_by_id,
        "actor": _actor_name(posted.created_by.user) if posted.created_by_id else None,
    }


def _actor_name(user) -> str:
    return getattr(user, "name", "") or user.get_username()


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


@contexts.get("/")
def context_list(request):
    return [
        _context_data(value)
        for value in CampaignContext.objects.filter(user=request.auth, is_active=True)
        .select_related("campaign", "character")
        .order_by("campaign__name", "kind")
    ]


@contexts.get("/{context_id}/")
def context_detail(request, context_id: int):
    context = _context_access(request, context_id)
    return {
        **_context_data(context),
        "id": context.campaign_id,
        "name": context.campaign.name,
        "is_game_master": context.kind == CampaignContext.Kind.GM,
        "use_shared_exp": context.campaign.use_shared_exp,
        "shared_experience": context.campaign.shared_experience,
        "item_sources": context.campaign.item_sources,
        "party_money": _party_money(context.campaign),
        "characters": [
            _character_data(value) for value in _visible_characters(context)
        ],
    }


@contexts.get("/{context_id}/characters/")
def character_list(request, context_id: int):
    context = _context_access(request, context_id)
    return [_character_data(value) for value in _visible_characters(context)]


@contexts.post("/{context_id}/characters/", response={201: dict})
def character_create(request, context_id: int, payload: CharacterCreate):
    context = _context_access(request, context_id)
    values = payload.model_dump()
    is_npc = values.pop("is_npc")
    if is_npc:
        _gm(context)
        character = Character.objects.create(
            campaign=context.campaign, is_active=True, **values
        )
        return 201, _character_data(character)
    if CampaignContext.objects.filter(
        campaign=context.campaign,
        user=context.user,
        kind=CampaignContext.Kind.PC,
        is_active=True,
    ).exists():
        raise HttpError(
            409, "This user already has an active player character in this campaign."
        )
    with db_transaction.atomic():
        pc_context = CampaignContext.objects.create(
            campaign=context.campaign, user=context.user, kind=CampaignContext.Kind.PC
        )
        character = Character.objects.create(
            campaign=context.campaign,
            context=pc_context,
            is_active=False,
            **values,
        )
        character.activate()
    return 201, _character_data(character)


@contexts.get("/{context_id}/characters/{character_id}/")
def character_detail(request, context_id: int, character_id: int):
    context = _context_access(request, context_id)
    character = _character(context, character_id)
    if not _visible_characters(context).filter(pk=character.pk).exists():
        raise HttpError(404, "Character not found.")
    return _character_data(character)


@contexts.patch("/{context_id}/characters/{character_id}/")
def character_update(
    request, context_id: int, character_id: int, payload: CharacterUpdate
):
    context = _context_access(request, context_id)
    character = _character(context, character_id)
    if context.kind != CampaignContext.Kind.GM and not _is_owner(context, character):
        raise HttpError(403, "You may only edit your own character.")
    updates = payload.model_dump(exclude_unset=True)
    skills = updates.pop("skill_proficiencies", None)
    if skills is not None:
        unknown = set(skills) - set(SKILL_NAMES)
        if unknown:
            raise HttpError(422, f"Unknown skills: {', '.join(sorted(unknown))}.")
        character.skill_proficiencies = skills
    for name, value in updates.items():
        setattr(character, name, value)
    try:
        character.full_clean()
        character.save()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return _character_data(character)


@contexts.delete("/{context_id}/characters/{character_id}/")
def character_archive(request, context_id: int, character_id: int):
    context = _context_access(request, context_id)
    character = _character(context, character_id)
    if context.kind != CampaignContext.Kind.GM and not _is_owner(context, character):
        raise HttpError(403, "You may only archive your own character.")
    character.is_archived, character.is_active, character.archived_at = (
        True,
        False,
        timezone.now(),
    )
    character.save(update_fields=("is_archived", "is_active", "archived_at"))
    if character.context_id:
        character.context.is_active = False
        character.context.save(update_fields=("is_active",))
    return _character_data(character)


@contexts.post("/{context_id}/character-imports/cah/preview")
def cah_preview(request, context_id: int, file: UploadedFile = File(...)):
    context = _context_access(request, context_id)
    if not file.name.lower().endswith(".cah"):
        raise HttpError(422, "Upload a .cah file.")
    try:
        preview = parse_cah(file.read())
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    token = secrets.token_urlsafe(24)
    cache.set(
        f"cah-import:{request.auth.pk}:{token}",
        {
            "campaign_id": context.campaign_id,
            "fields": preview.fields,
            "warnings": preview.warnings,
        },
        timeout=900,
    )
    return {"token": token, "fields": preview.fields, "warnings": preview.warnings}


@contexts.post(
    "/{context_id}/character-imports/cah/commit", response={201: dict, 200: dict}
)
def cah_commit(request, context_id: int, payload: CahCommit):
    context = _context_access(request, context_id)
    key = f"cah-import:{request.auth.pk}:{payload.token}"
    draft = cache.get(key)
    if not draft or draft["campaign_id"] != context.campaign_id:
        raise HttpError(422, "This import preview has expired or is invalid.")
    fields = draft["fields"]
    target = _character(context, payload.character_id) if payload.character_id else None
    if target:
        if not _is_owner(context, target):
            raise HttpError(403, "You may only replace your own character.")
        for name, value in fields.items():
            setattr(target, name, value)
        target.full_clean()
        target.save()
        cache.delete(key)
        return 200, _character_data(target)
    if CampaignContext.objects.filter(
        campaign=context.campaign,
        user=context.user,
        kind=CampaignContext.Kind.PC,
        is_active=True,
    ).exists():
        raise HttpError(409, "Select your existing player character to replace it.")
    defaults = {
        "name": "Imported character",
        "race": "",
        "character_class": "",
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    }
    defaults.update(fields)
    with db_transaction.atomic():
        pc_context = CampaignContext.objects.create(
            campaign=context.campaign, user=context.user, kind=CampaignContext.Kind.PC
        )
        target = Character.objects.create(
            campaign=context.campaign, context=pc_context, is_active=True, **defaults
        )
        target.activate()
    cache.delete(key)
    return 201, _character_data(target)


@contexts.get("/{context_id}/items/")
def item_list(request, context_id: int):
    context = _context_access(request, context_id)
    return [_item_data(item) for item in _items(context.campaign).order_by("name")]


@contexts.post("/{context_id}/items/", response={201: dict})
def item_create(request, context_id: int, payload: ItemCreate):
    context = _context_access(request, context_id)
    item = InventoryItem(
        campaign=context.campaign,
        created_by=context,
        name=payload.name.strip(),
        description=payload.description,
    )
    try:
        item.full_clean()
        item.save()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _item_data(item)


def _editable_item(context: CampaignContext, item_id: int) -> InventoryItem:
    item = get_object_or_404(_items(context.campaign), pk=item_id)
    if item.campaign_id is None:
        raise HttpError(403, "Imported catalogue items are read-only.")
    _gm(context)
    return item


@contexts.patch("/{context_id}/items/{item_id}/")
def item_update(request, context_id: int, item_id: int, payload: ItemUpdate):
    item = _editable_item(_context_access(request, context_id), item_id)
    for name, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, name, value.strip() if name == "name" and value else value)
    try:
        item.full_clean()
        item.save()
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return _item_data(item)


@contexts.delete("/{context_id}/items/{item_id}/", response={204: None})
def item_delete(request, context_id: int, item_id: int):
    item = _editable_item(_context_access(request, context_id), item_id)
    if item.entries.exists():
        raise HttpError(409, "Items referenced by ledger entries cannot be deleted.")
    item.delete()
    return 204, None


def _coin_amounts(amounts: dict[str, int]) -> dict[MoneyEntry.Denomination, int]:
    result = {}
    for denomination, amount in amounts.items():
        try:
            key = MoneyEntry.Denomination(denomination)
        except ValueError as error:
            raise HttpError(422, "Unknown currency denomination.") from error
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise HttpError(422, "Coin amounts must be positive integers.")
        result[key] = amount
    if not result:
        raise HttpError(422, "At least one coin amount is required.")
    return result


def _can_act_for(context: CampaignContext, character: Character) -> bool:
    return context.kind == CampaignContext.Kind.GM or _is_owner(context, character)


@contexts.post("/{context_id}/inventory-transactions/", response={201: dict})
def inventory_transaction_create(
    request, context_id: int, payload: InventoryTransactionCreate
):
    context = _context_access(request, context_id)
    source = (
        _character(context, payload.from_character_id)
        if payload.from_character_id
        else None
    )
    destination = (
        _character(context, payload.to_character_id)
        if payload.to_character_id
        else None
    )
    if source is None and destination is None:
        raise HttpError(422, "An inventory transaction needs a source or destination.")
    if (
        context.kind != CampaignContext.Kind.GM
        and source
        and not _can_act_for(context, source)
    ):
        raise HttpError(
            403, "Players may only transfer inventory from their own character."
        )
    item = get_object_or_404(_items(context.campaign), pk=payload.item_id)
    if source and source.inventory.get(item, 0) < payload.quantity:
        raise HttpError(
            422, "A character cannot transfer more of an item than they hold."
        )
    try:
        posted = post_inventory_transaction(
            from_account=source.inventory_account()
            if source
            else context.campaign.inventory_system_account(),
            to_account=destination.inventory_account()
            if destination
            else context.campaign.inventory_system_account(),
            item=item,
            quantity=payload.quantity,
            description=payload.description,
        )
        posted.created_by = context
        posted.save(update_fields=("created_by",))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _transaction_data(posted)


@contexts.post("/{context_id}/money-transfers/", response={201: dict})
def money_transfer_create(request, context_id: int, payload: MoneyTransferCreate):
    context = _context_access(request, context_id)
    source = (
        _character(context, payload.from_character_id)
        if payload.from_character_id
        else None
    )
    destination = (
        _character(context, payload.to_character_id)
        if payload.to_character_id
        else None
    )
    if source is None and destination is None:
        raise HttpError(422, "A money transfer needs a source or destination.")
    if context.kind != CampaignContext.Kind.GM and (
        source is None or not _can_act_for(context, source)
    ):
        raise HttpError(
            403, "Players may only transfer money from their own character."
        )
    amounts = _coin_amounts(payload.amounts)
    if source:
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
        posted = post_money_transaction(
            [
                (
                    source.money_account()
                    if source
                    else context.campaign.money_system_account(),
                    denomination,
                    -amount,
                )
                for denomination, amount in amounts.items()
            ]
            + [
                (
                    destination.money_account()
                    if destination
                    else context.campaign.money_system_account(),
                    denomination,
                    amount,
                )
                for denomination, amount in amounts.items()
            ],
            description=payload.description,
        )
        posted.created_by = context
        posted.save(update_fields=("created_by",))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _transaction_data(posted)


@contexts.post("/{context_id}/money-exchanges/", response={201: dict})
def money_exchange_create(request, context_id: int, payload: MoneyExchangeCreate):
    context = _context_access(request, context_id)
    character = _character(context, payload.character_id)
    if not _can_act_for(context, character):
        raise HttpError(403, "Players may only exchange their own coins.")
    try:
        posted = exchange_coins(
            character=character,
            given=_coin_amounts(payload.given),
            received=_coin_amounts(payload.received),
            description=payload.description,
        )
        posted.created_by = context
        posted.save(update_fields=("created_by",))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _transaction_data(posted)


@contexts.post("/{context_id}/shared-xp-awards/", response={201: dict})
def shared_xp_award_create(request, context_id: int, payload: SharedXpAwardCreate):
    context = _context_access(request, context_id)
    _gm(context)
    try:
        _, posted = context.campaign.award_shared_experience(
            payload.amount,
            description=payload.description,
            created_by=context,
            return_transaction=True,
        )
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return 201, _transaction_data(posted)


def _history_data(posted):
    data = _transaction_data(posted)
    entries = []
    for entry in posted.entries.all():
        value = {
            "account_id": entry.account_id,
            "account_name": f"Campaign {data['ledger']} system"
            if entry.account.is_system
            else entry.account.character.name,
            "is_system_account": entry.account.is_system,
            "amount": entry.amount,
        }
        if isinstance(entry, InventoryEntry):
            value.update(item_id=entry.item_id, item_name=entry.item.name)
        if isinstance(entry, MoneyEntry):
            value["denomination"] = entry.denomination
        entries.append(value)
    data.update(
        entries=entries,
        reversal_of_id=posted.reversal_of_id,
        is_reversed=hasattr(posted, "reversal"),
    )
    return data


TRANSACTION_MODELS = {
    "inventory": InventoryTransaction,
    "money": MoneyTransaction,
    "experience": ExperienceTransaction,
}


def _transaction_queryset(model, campaign):
    entry_model = model._meta.get_field("entries").related_model
    entries = entry_model.objects.select_related(
        "account__character", *(("item",) if model is InventoryTransaction else ())
    )
    return model.objects.filter(campaign=campaign).select_related(
        "created_by__user"
    ).prefetch_related(
        Prefetch("entries", queryset=entries)
    )


@contexts.get("/{context_id}/transactions/")
def transaction_list(
    request,
    context_id: int,
    ledger: Literal["all", "inventory", "money", "experience"] = "all",
    character_id: int | None = None,
    page: int = 1,
    page_size: int = 25,
):
    context = _context_access(request, context_id)
    if page < 1 or not 1 <= page_size <= 100:
        raise HttpError(
            422, "page must be positive and page_size must be between 1 and 100."
        )
    choices = (
        TRANSACTION_MODELS.items()
        if ledger == "all"
        else ((ledger, TRANSACTION_MODELS[ledger]),)
    )
    rows = []
    character = (
        _character(context, character_id) if character_id is not None else None
    )
    for _, model in choices:
        query = _transaction_queryset(model, context.campaign)
        if character:
            query = query.filter(entries__account__character=character).distinct()
        if context.kind != CampaignContext.Kind.GM:
            query = query.filter(
                entries__account__character__context__user=context.user
            ).distinct()
        rows.extend(query)
    rows.sort(key=lambda posted: (posted.created_at, posted.pk), reverse=True)
    start = (page - 1) * page_size
    return {
        "count": len(rows),
        "page": page,
        "page_size": page_size,
        "results": [
            _history_data(posted) for posted in rows[start : start + page_size]
        ],
    }


@contexts.delete("/{context_id}/transactions/{ledger}/{transaction_id}/")
def transaction_reverse(
    request,
    context_id: int,
    ledger: Literal["inventory", "money", "experience"],
    transaction_id: int,
):
    context = _context_access(request, context_id)
    model = TRANSACTION_MODELS[ledger]
    original = get_object_or_404(model, pk=transaction_id, campaign=context.campaign)
    latest = (
        model.objects.filter(campaign=context.campaign)
        .order_by("-created_at", "-pk")
        .first()
    )
    if latest is None or latest.pk != original.pk:
        raise HttpError(
            409, "Only the latest transaction in this ledger may be reversed."
        )
    if original.reversal_of_id or hasattr(original, "reversal"):
        raise HttpError(409, "Reversal transactions are final.")
    if context.kind != CampaignContext.Kind.GM and original.created_by_id != context.pk:
        raise HttpError(
            403, "Only the initiator or a game master may reverse this transaction."
        )
    try:
        reversed_posted = reverse_transaction(original)
        reversed_posted.created_by = context
        reversed_posted.save(update_fields=("created_by",))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    return _history_data(reversed_posted)


@contexts.get("/{context_id}/manage/contexts/")
def managed_context_list(request, context_id: int):
    context = _context_access(request, context_id)
    _gm(context)
    return [
        {
            **_context_data(candidate),
            "username": candidate.user.get_username(),
            "is_game_master": candidate.kind == CampaignContext.Kind.GM,
            "is_active": candidate.is_active,
        }
        for candidate in CampaignContext.objects.filter(
            campaign=context.campaign
        ).select_related("campaign", "user", "character")
    ]


@contexts.post("/{context_id}/manage/users/", response={201: dict})
def managed_user_create(request, context_id: int, payload: UserCreate):
    context = _context_access(request, context_id)
    _gm(context)
    user_model = get_user_model()
    if user_model.objects.filter(username=payload.username).exists():
        raise HttpError(409, "That username already exists.")
    if payload.email and user_model.objects.filter(email=payload.email).exists():
        raise HttpError(409, "That email address already exists.")
    password = " ".join(secrets.choice(PASSWORD_WORDS) for _ in range(5))
    user = user_model.objects.create_user(
        username=payload.username, email=payload.email, password=password
    )
    return 201, {"id": user.pk, "username": user.get_username(), "password": password}


@contexts.post("/{context_id}/manage/contexts/", response={201: dict})
def managed_context_create(request, context_id: int, payload: ContextCreate):
    context = _context_access(request, context_id)
    _gm(context)
    user = get_object_or_404(get_user_model(), username=payload.username)
    candidate, created = CampaignContext.objects.get_or_create(
        campaign=context.campaign, user=user, kind=payload.kind
    )
    if not created and candidate.is_active:
        raise HttpError(409, "That context already exists.")
    if not candidate.is_active:
        candidate.is_active = True
        candidate.save(update_fields=("is_active",))
    if candidate.kind == CampaignContext.Kind.PC and not hasattr(
        candidate, "character"
    ):
        character = Character.objects.create(
            campaign=context.campaign,
            context=candidate,
            is_active=False,
            name=user.get_username(),
            race="",
            character_class="",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )
        character.activate()
    return 201, _context_data(candidate)


@contexts.delete(
    "/{context_id}/manage/contexts/{managed_context_id}/", response={204: None}
)
def managed_context_deactivate(request, context_id: int, managed_context_id: int):
    context = _context_access(request, context_id)
    _gm(context)
    candidate = get_object_or_404(
        CampaignContext,
        pk=managed_context_id,
        campaign=context.campaign,
        is_active=True,
    )
    candidate.is_active = False
    candidate.save(update_fields=("is_active",))
    if candidate.kind == CampaignContext.Kind.PC and hasattr(candidate, "character"):
        (
            candidate.character.is_active,
            candidate.character.is_archived,
            candidate.character.archived_at,
        ) = False, True, timezone.now()
        candidate.character.save(
            update_fields=("is_active", "is_archived", "archived_at")
        )
    return 204, None


api.add_router("/contexts", contexts)
