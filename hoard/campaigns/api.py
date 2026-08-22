from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Annotated, Literal

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.db.models import Prefetch, Q, Sum
from django.db.models.fields.json import KeyTextTransform
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import File, NinjaAPI, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth
from pydantic import Field

from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)

from .models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterCompanion,
    CharacterFeature,
    CharacterLoadout,
    CharacterNote,
    CharacterSpell,
    ExperienceTransaction,
    InventoryEntry,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
)
from .realtime import notify_campaign_changed
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
    background: str | None = None
    base_hp: int | None = None
    current_hp: int | None = None
    temporary_hp: int | None = None
    base_ac: int | None = None
    ac_adjustment: int | None = None
    speed: str | None = None
    spell_slots: dict[str, int] | None = None
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


class CalendarAdjustment(Schema):
    amount: Literal[-1, 1]


class CahCommit(Schema):
    token: str
    character_id: int | None = None
    inventory: list[dict[str, object]] = []


class SheetRecord(Schema):
    name: str = ""
    title: str = ""
    body: str = ""
    description: str = ""
    notes: str = ""
    kind: Literal["feat", "feature"] = "feat"
    level: int = 0
    prepared: bool = True
    catalogue_entry_id: int | None = None
    item_id: int | None = None
    equipped: bool = False
    label: str = ""
    armor_class: int = 10
    max_hp: int = 1
    current_hp: int = 1
    speed: str = ""
    abilities: dict[str, int | None] = {}
    attacks: list[dict[str, object]] = []
    monster_template_id: int | None = None


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


def _calendar_data(campaign: Campaign) -> dict[str, int | str]:
    return {
        "era_abbreviation": campaign.calendar_era_abbreviation,
        "era_name": campaign.calendar_era_name,
        "year": campaign.calendar_year,
        "day": campaign.calendar_day,
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
        "current_hp": character.current_hp,
        "temporary_hp": character.temporary_hp,
        "base_ac": character.base_ac,
        "ac_adjustment": character.ac_adjustment,
        "armor_class": character.base_ac + character.ac_adjustment,
        "speed": character.speed,
        "spell_slots": character.spell_slots,
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
        "background": character.background,
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
        "notes": [
            {"id": note.pk, "title": note.title, "body": note.body}
            for note in character.notes.all()
        ],
        "features": [
            {
                "id": feature.pk,
                "kind": feature.kind,
                "name": feature.name,
                "description": feature.description,
                "notes": feature.notes,
                "catalogue_entry_id": feature.catalogue_entry_id,
            }
            for feature in character.features.select_related("catalogue_entry").all()
        ],
        "spells": [
            {
                "id": spell.pk,
                "name": spell.name,
                "level": spell.level,
                "description": spell.description,
                "notes": spell.notes,
                "prepared": spell.prepared,
                "catalogue_entry_id": spell.catalogue_entry_id,
            }
            for spell in character.spells.select_related("catalogue_entry").all()
        ],
        "loadout": [
            {
                "id": loadout.pk,
                "item_id": loadout.item_id,
                "name": loadout.item.name,
                "equipped": loadout.equipped,
                "label": loadout.label,
            }
            for loadout in character.loadout.select_related("item").all()
        ],
        "companions": [
            {
                "id": companion.pk,
                "name": companion.name,
                "armor_class": companion.armor_class,
                "max_hp": companion.max_hp,
                "current_hp": companion.current_hp,
                "speed": companion.speed,
                "abilities": companion.abilities,
                "attacks": companion.attacks,
                "notes": companion.notes,
                "monster_template_id": companion.monster_template_id,
            }
            for companion in character.companions.select_related(
                "monster_template"
            ).all()
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


def _item_data(item: CompendiumEntry) -> dict[str, object]:
    return {
        "id": item.pk,
        "name": item.name,
        "description": item.description,
        "campaign_id": item.source.repository.campaign_id,
        "created_by_id": None,
        "created_by_username": None,
        "source_system": item.source.name,
        "source_identifier": item.source_identifier or None,
        "source_repository": item.source.repository.repository_url or None,
        "equipment": {
            "category": item.kind if item.kind in {"item", "weapon", "armor"} else None,
            "source_book": item.source_book or None,
            "item_type": getattr(item, "compendium_item_type", None),
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
        "is_imported": True,
    }


def _items(campaign: Campaign):
    return (
        CompendiumEntry.objects.filter(
            source__in=campaign.compendium_sources.all(),
            kind__in=("item", "weapon", "armor"),
        )
        .select_related("source", "source__repository")
        .annotate(compendium_item_type=KeyTextTransform("item_type", "data"))
        .defer("data", "source__data", "source__repository__data")
    )


def _source_data(source: CompendiumSource, enabled: bool) -> dict[str, object]:
    return {
        "id": source.pk,
        "identifier": source.identifier,
        "name": source.name,
        "repository": source.repository.name,
        "campaign_id": source.repository.campaign_id,
        "enabled": enabled,
        "entry_count": source.entries.count(),
    }


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
        "calendar": _calendar_data(context.campaign),
        "party_money": _party_money(context.campaign),
        "characters": [
            _character_data(value) for value in _visible_characters(context)
        ],
    }


@contexts.get("/{context_id}/calendar/")
def calendar_detail(request, context_id: int):
    return _calendar_data(_context_access(request, context_id).campaign)


@contexts.post("/{context_id}/calendar/adjust/")
def calendar_adjust(request, context_id: int, payload: CalendarAdjustment):
    context = _context_access(request, context_id)
    _gm(context)
    try:
        context.campaign.adjust_calendar_day(payload.amount)
        context.campaign.full_clean()
        context.campaign.save(update_fields=("calendar_year", "calendar_day"))
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    notify_campaign_changed(context.campaign_id)
    return _calendar_data(context.campaign)


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
        notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
    return _character_data(character)


def _editable_sheet_character(context: CampaignContext, character_id: int) -> Character:
    character = _character(context, character_id)
    if context.kind != CampaignContext.Kind.GM and not _is_owner(context, character):
        raise HttpError(403, "You may only edit your own character.")
    return character


def _enabled_entry(campaign: Campaign, entry_id: int | None, kind: str | None = None):
    if entry_id is None:
        return None
    query = CompendiumEntry.objects.filter(
        pk=entry_id, source__in=campaign.compendium_sources.all()
    )
    if kind:
        query = query.filter(kind=kind)
    return get_object_or_404(query)


@contexts.post("/{context_id}/characters/{character_id}/notes/", response={201: dict})
def note_create(request, context_id: int, character_id: int, payload: SheetRecord):
    character = _editable_sheet_character(
        _context_access(request, context_id), character_id
    )
    note = CharacterNote.objects.create(
        character=character, title=payload.title, body=payload.body
    )
    return 201, {"id": note.pk, "title": note.title, "body": note.body}


@contexts.post(
    "/{context_id}/characters/{character_id}/features/", response={201: dict}
)
def feature_create(request, context_id: int, character_id: int, payload: SheetRecord):
    context = _context_access(request, context_id)
    character = _editable_sheet_character(context, character_id)
    entry = _enabled_entry(context.campaign, payload.catalogue_entry_id, "feat")
    feature = CharacterFeature.objects.create(
        character=character,
        kind=payload.kind,
        catalogue_entry=entry,
        name=payload.name or (entry.name if entry else ""),
        description=payload.description,
        notes=payload.notes,
    )
    return 201, {"id": feature.pk}


@contexts.post("/{context_id}/characters/{character_id}/spells/", response={201: dict})
def spell_create(request, context_id: int, character_id: int, payload: SheetRecord):
    context = _context_access(request, context_id)
    character = _editable_sheet_character(context, character_id)
    entry = _enabled_entry(context.campaign, payload.catalogue_entry_id, "spell")
    spell = CharacterSpell.objects.create(
        character=character,
        catalogue_entry=entry,
        name=payload.name or (entry.name if entry else ""),
        level=payload.level,
        description=payload.description,
        notes=payload.notes,
        prepared=payload.prepared,
    )
    return 201, {"id": spell.pk}


@contexts.post("/{context_id}/characters/{character_id}/loadout/", response={201: dict})
def loadout_create(request, context_id: int, character_id: int, payload: SheetRecord):
    context = _context_access(request, context_id)
    character = _editable_sheet_character(context, character_id)
    item = _enabled_entry(context.campaign, payload.item_id)
    if item.kind not in {"item", "weapon", "armor"}:
        raise HttpError(422, "Loadout entries must be equipment.")
    loadout, _ = CharacterLoadout.objects.update_or_create(
        character=character,
        item=item,
        defaults={"equipped": payload.equipped, "label": payload.label},
    )
    return 201, {"id": loadout.pk}


@contexts.patch("/{context_id}/characters/{character_id}/loadout/{record_id}/")
def loadout_update(
    request, context_id: int, character_id: int, record_id: int, payload: SheetRecord
):
    context = _context_access(request, context_id)
    loadout = _sheet_record(context, character_id, CharacterLoadout, record_id)
    if "item_id" in payload.model_fields_set:
        item = _enabled_entry(context.campaign, payload.item_id)
        if item.kind not in {"item", "weapon", "armor"}:
            raise HttpError(422, "Loadout entries must be equipment.")
        loadout.item = item
    for field in ("equipped", "label"):
        if field in payload.model_fields_set:
            setattr(loadout, field, getattr(payload, field))
    loadout.save()
    return {"id": loadout.pk}


@contexts.delete(
    "/{context_id}/characters/{character_id}/loadout/{record_id}/", response={204: None}
)
def loadout_delete(request, context_id: int, character_id: int, record_id: int):
    _sheet_record(
        _context_access(request, context_id), character_id, CharacterLoadout, record_id
    ).delete()
    return 204, None


@contexts.post(
    "/{context_id}/characters/{character_id}/companions/", response={201: dict}
)
def companion_create(request, context_id: int, character_id: int, payload: SheetRecord):
    context = _context_access(request, context_id)
    character = _editable_sheet_character(context, character_id)
    template = _enabled_entry(context.campaign, payload.monster_template_id, "monster")
    companion = CharacterCompanion.objects.create(
        character=character,
        monster_template=template,
        name=payload.name,
        armor_class=payload.armor_class,
        max_hp=payload.max_hp,
        current_hp=payload.current_hp,
        speed=payload.speed,
        abilities=payload.abilities,
        attacks=payload.attacks,
        notes=payload.notes,
    )
    return 201, {"id": companion.pk}


def _sheet_record(context: CampaignContext, character_id: int, model, record_id: int):
    character = _editable_sheet_character(context, character_id)
    return get_object_or_404(model, pk=record_id, character=character)


@contexts.patch("/{context_id}/characters/{character_id}/notes/{record_id}/")
def note_update(
    request, context_id: int, character_id: int, record_id: int, payload: SheetRecord
):
    context = _context_access(request, context_id)
    note = _sheet_record(context, character_id, CharacterNote, record_id)
    for field in ("title", "body"):
        if field in payload.model_fields_set:
            setattr(note, field, getattr(payload, field))
    note.save()
    return {"id": note.pk, "title": note.title, "body": note.body}


@contexts.delete(
    "/{context_id}/characters/{character_id}/notes/{record_id}/", response={204: None}
)
def note_delete(request, context_id: int, character_id: int, record_id: int):
    note = _sheet_record(
        _context_access(request, context_id), character_id, CharacterNote, record_id
    )
    note.delete()
    return 204, None


@contexts.patch("/{context_id}/characters/{character_id}/features/{record_id}/")
def feature_update(
    request, context_id: int, character_id: int, record_id: int, payload: SheetRecord
):
    context = _context_access(request, context_id)
    feature = _sheet_record(context, character_id, CharacterFeature, record_id)
    if "catalogue_entry_id" in payload.model_fields_set:
        feature.catalogue_entry = _enabled_entry(
            context.campaign, payload.catalogue_entry_id, "feat"
        )
    for field in ("kind", "name", "description", "notes"):
        if field in payload.model_fields_set:
            setattr(feature, field, getattr(payload, field))
    feature.save()
    return {"id": feature.pk}


@contexts.delete(
    "/{context_id}/characters/{character_id}/features/{record_id}/",
    response={204: None},
)
def feature_delete(request, context_id: int, character_id: int, record_id: int):
    _sheet_record(
        _context_access(request, context_id), character_id, CharacterFeature, record_id
    ).delete()
    return 204, None


@contexts.patch("/{context_id}/characters/{character_id}/spells/{record_id}/")
def spell_update(
    request, context_id: int, character_id: int, record_id: int, payload: SheetRecord
):
    context = _context_access(request, context_id)
    spell = _sheet_record(context, character_id, CharacterSpell, record_id)
    if "catalogue_entry_id" in payload.model_fields_set:
        spell.catalogue_entry = _enabled_entry(
            context.campaign, payload.catalogue_entry_id, "spell"
        )
    for field in ("name", "level", "description", "notes", "prepared"):
        if field in payload.model_fields_set:
            setattr(spell, field, getattr(payload, field))
    spell.save()
    return {"id": spell.pk}


@contexts.delete(
    "/{context_id}/characters/{character_id}/spells/{record_id}/", response={204: None}
)
def spell_delete(request, context_id: int, character_id: int, record_id: int):
    _sheet_record(
        _context_access(request, context_id), character_id, CharacterSpell, record_id
    ).delete()
    return 204, None


@contexts.patch("/{context_id}/characters/{character_id}/companions/{record_id}/")
def companion_update(
    request, context_id: int, character_id: int, record_id: int, payload: SheetRecord
):
    context = _context_access(request, context_id)
    companion = _sheet_record(context, character_id, CharacterCompanion, record_id)
    if "monster_template_id" in payload.model_fields_set:
        companion.monster_template = _enabled_entry(
            context.campaign, payload.monster_template_id, "monster"
        )
    for field in (
        "name",
        "armor_class",
        "max_hp",
        "current_hp",
        "speed",
        "abilities",
        "attacks",
        "notes",
    ):
        if field in payload.model_fields_set:
            setattr(companion, field, getattr(payload, field))
    companion.save()
    return {"id": companion.pk}


@contexts.delete(
    "/{context_id}/characters/{character_id}/companions/{record_id}/",
    response={204: None},
)
def companion_delete(request, context_id: int, character_id: int, record_id: int):
    _sheet_record(
        _context_access(request, context_id),
        character_id,
        CharacterCompanion,
        record_id,
    ).delete()
    return 204, None


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
    notify_campaign_changed(context.campaign_id)
    return _character_data(character)


def _available_entries(campaign: Campaign, kind: str):
    return CompendiumEntry.objects.filter(
        source__in=campaign.compendium_sources.all(), kind=kind
    ).select_related("source", "source__repository")


def _custom_source(campaign: Campaign) -> CompendiumSource:
    repository, _ = CompendiumRepository.objects.get_or_create(
        identifier=f"campaign-{campaign.pk}-custom",
        defaults={
            "name": f"{campaign.name} custom content",
            "campaign": campaign,
        },
    )
    source, _ = CompendiumSource.objects.get_or_create(
        repository=repository,
        identifier="custom",
        defaults={"name": "Custom content"},
    )
    campaign.compendium_sources.add(source)
    return source


def _match_import_entry(campaign: Campaign, row: dict[str, object]) -> int | None:
    entries = _available_entries(campaign, str(row["kind"]))
    identifier = str(row.get("source_identifier") or "")
    if identifier:
        matched = list(entries.filter(source_identifier=identifier)[:2])
        if len(matched) == 1:
            return matched[0].pk
    matched = list(entries.filter(name__iexact=str(row["name"]))[:2])
    return matched[0].pk if len(matched) == 1 else None


def _calculated_values(character: Character) -> dict[str, object]:
    sheet = _sheet_data(character)
    return {
        "max_hp": sheet["max_hp"],
        "armor_class": sheet["armor_class"],
        "proficiency_bonus": sheet["proficiency_bonus"],
        "ability_modifiers": {
            ability: sheet["abilities"][ability]["modifier"] for ability in ABILITIES
        },
        "saves": {ability: sheet["saves"][ability]["bonus"] for ability in ABILITIES},
        "skills": {skill: sheet["skills"][skill]["bonus"] for skill in SKILL_NAMES},
    }


@contexts.post("/{context_id}/character-imports/cah/preview")
def cah_preview(
    request,
    context_id: int,
    file: UploadedFile = File(...),
    character_id: int | None = None,
):
    context = _context_access(request, context_id)
    if not file.name.lower().endswith(".cah"):
        raise HttpError(422, "Upload a .cah file.")
    try:
        preview = parse_cah(file.read())
    except DjangoValidationError as error:
        raise _unprocessable(error) from error
    target = _character(context, character_id) if character_id else None
    if target and not (
        context.kind == CampaignContext.Kind.GM or _is_owner(context, target)
    ):
        raise HttpError(403, "You may only import into your own character.")
    inventory = [
        {**row, "matched_item_id": _match_import_entry(context.campaign, row)}
        for row in preview.inventory
    ]
    before = _calculated_values(target) if target else None
    if target:
        candidate = Character.objects.get(pk=target.pk)
        for name, value in preview.fields.items():
            setattr(candidate, name, value)
        after = _calculated_values(candidate)
    else:
        after = None
    token = secrets.token_urlsafe(24)
    cache.set(
        f"cah-import:{request.auth.pk}:{token}",
        {
            "campaign_id": context.campaign_id,
            "fields": preview.fields,
            "collections": preview.collections,
            "inventory": inventory,
            "warnings": preview.warnings,
        },
        timeout=900,
    )
    return {
        "token": token,
        "fields": preview.fields,
        "collections": preview.collections,
        "inventory": inventory,
        "warnings": preview.warnings,
        "calculated_before": before,
        "calculated_after": after,
    }


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
        if not (context.kind == CampaignContext.Kind.GM or _is_owner(context, target)):
            raise HttpError(403, "You may only replace your own character.")
        status = 200
    else:
        if CampaignContext.objects.filter(
            campaign=context.campaign,
            user=context.user,
            kind=CampaignContext.Kind.PC,
            is_active=True,
        ).exists():
            raise HttpError(409, "Select your existing player character to replace it.")
        status = 201
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
                campaign=context.campaign,
                user=context.user,
                kind=CampaignContext.Kind.PC,
            )
            target = Character.objects.create(
                campaign=context.campaign,
                context=pc_context,
                is_active=True,
                **defaults,
            )
            target.activate()
    with db_transaction.atomic():
        for name, value in fields.items():
            setattr(target, name, value)
        target.full_clean()
        target.save()
        target.notes.all().delete()
        target.features.all().delete()
        target.spells.all().delete()
        target.loadout.all().delete()
        target.companions.all().delete()
        CharacterNote.objects.bulk_create(
            [
                CharacterNote(character=target, title=row["title"], body=row["body"])
                for row in draft["collections"]["notes"]
            ]
        )
        for row in draft["collections"]["features"]:
            entry_id = _match_import_entry(context.campaign, {**row, "kind": "feat"})
            CharacterFeature.objects.create(
                character=target,
                kind=row["kind"],
                name=row["name"],
                description=row["description"],
                notes=row["notes"],
                catalogue_entry_id=entry_id,
            )
        for row in draft["collections"]["spells"]:
            entry_id = _match_import_entry(context.campaign, {**row, "kind": "spell"})
            CharacterSpell.objects.create(
                character=target,
                name=row["name"],
                level=row["level"],
                description=row["description"],
                notes=row["notes"],
                catalogue_entry_id=entry_id,
            )
        for row in draft["collections"]["companions"]:
            entry_id = _match_import_entry(context.campaign, {**row, "kind": "monster"})
            CharacterCompanion.objects.create(
                character=target,
                name=row["name"],
                armor_class=row["armor_class"],
                max_hp=row["max_hp"],
                current_hp=row["current_hp"],
                speed=row["speed"],
                abilities=row["abilities"],
                attacks=row["attacks"],
                notes=row["description"],
                monster_template_id=entry_id,
            )
        draft_rows = {row["line_id"]: row for row in draft["inventory"]}
        for selected in payload.inventory:
            line = draft_rows.get(selected.get("line_id"))
            if not line or selected.get("action") != "add":
                continue
            quantity = selected.get("quantity", line["quantity"])
            if not isinstance(quantity, int) or quantity < 1:
                raise HttpError(422, "Imported inventory quantities must be positive.")
            item_id = selected.get("item_id") or line.get("matched_item_id")
            item = None
            if isinstance(item_id, int):
                item = _items(context.campaign).filter(pk=item_id).first()
                if not item:
                    raise HttpError(
                        422,
                        "Selected Compendium item is not enabled for this campaign.",
                    )
            if item is None:
                source = _custom_source(context.campaign)
                item = CompendiumEntry.objects.create(
                    source=source,
                    kind=line["kind"],
                    name=line["name"],
                    description=line["description"],
                    source_identifier=f"cah:{secrets.token_urlsafe(12)}",
                    data={"cah_import": line["raw"]},
                    created_by=context,
                )
            posted = post_inventory_transaction(
                from_account=context.campaign.inventory_system_account(),
                to_account=target.inventory_account(),
                item=item,
                quantity=quantity,
                description="Imported from 5e Companion",
            )
            posted.created_by = context
            posted.save(update_fields=("created_by",))
            if line.get("equipped"):
                CharacterLoadout.objects.get_or_create(
                    character=target, item=item, defaults={"equipped": True}
                )
    cache.delete(key)
    notify_campaign_changed(context.campaign_id)
    return status, _character_data(target)


def _editable_item(context: CampaignContext, item_id: int) -> CompendiumEntry:
    item = get_object_or_404(_items(context.campaign), pk=item_id)
    if item.source.repository.campaign_id != context.campaign_id:
        raise HttpError(403, "Imported catalogue items are read-only.")
    _gm(context)
    return item


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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
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
    return (
        model.objects.filter(campaign=campaign)
        .select_related("created_by__user")
        .prefetch_related(Prefetch("entries", queryset=entries))
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
    character = _character(context, character_id) if character_id is not None else None
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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
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
    notify_campaign_changed(context.campaign_id)
    return 204, None


api.add_router("/contexts", contexts)
