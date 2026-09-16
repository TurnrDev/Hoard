from __future__ import annotations

from decimal import Decimal
from typing import Literal

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q, Sum
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import (
    Campaign,
    CampaignContext,
    Character,
    ExperienceTransaction,
    MoneyEntry,
    MoneyTransaction,
)
from .realtime import notify_campaign_changed
from .services import exchange_coins, reverse_transaction
from .services.ledger import post_money_transaction


class Credentials(Schema):
    username: str
    password: str


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


api = NinjaAPI(title="Hoard API", version="0.1.1", auth=django_auth)


def unprocessable(error: DjangoValidationError) -> HttpError:
    messages = error.message_dict if hasattr(error, "message_dict") else error.messages
    return HttpError(422, str(messages))


def context_access(request, context_id: int) -> CampaignContext:
    return get_object_or_404(
        CampaignContext.objects.select_related("campaign", "user", "character"),
        pk=context_id,
        user=request.auth,
        is_active=True,
    )


def gm_context(context: CampaignContext) -> None:
    if context.kind != CampaignContext.Kind.GM:
        raise HttpError(403, "This action requires a game-master context.")


def character_for_context(
    context: CampaignContext, character_id: int | None
) -> Character:
    if character_id is None:
        raise HttpError(422, "A character id is required.")
    return get_object_or_404(Character, pk=character_id, campaign=context.campaign)


def is_character_owner(context: CampaignContext, character: Character) -> bool:
    return (
        character.context_id is not None
        and character.context.user_id == context.user_id
    )


def editable_character(context: CampaignContext, character_id: int) -> Character:
    character = character_for_context(context, character_id)
    if context.kind != CampaignContext.Kind.GM and not is_character_owner(
        context, character
    ):
        raise HttpError(403, "You may only edit your own character.")
    return character


def visible_characters(context: CampaignContext):
    if context.kind == CampaignContext.Kind.GM:
        return context.campaign.characters.all()

    return context.campaign.characters.filter(
        Q(is_active=True) | Q(context__user=context.user)
    )


def context_data(context: CampaignContext) -> dict[str, object]:
    character = getattr(context, "character", None)
    return {
        "id": context.pk,
        "campaign_id": context.campaign_id,
        "campaign_name": context.campaign.name,
        "kind": context.kind,
        "character_id": character.pk if character else None,
        "character_name": character.name if character else None,
    }


def money_data(character: Character) -> dict[str, int | str]:
    return {
        "cp": character.money.copper,
        "sp": character.money.silver,
        "ep": character.money.electrum,
        "gp": character.money.gold,
        "pp": character.money.platinum,
        "gold_value": str(character.money.gold_value),
    }


ABILITIES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)
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


def calculation(
    value: int, base: int, components: list[dict[str, object]]
) -> dict[str, object]:
    return {"value": value, "base": base, "components": components}


def character_sheet_data(character: Character) -> dict[str, object]:
    hp_modifier = character.ability_modifier(character.hp_ability)
    initiative_half = character.half_proficiency("dexterity", "none")
    base_proficiency = 2 + (character.level - 1) // 4
    return {
        "level": character.level,
        "rolled_hit_points": character.rolled_hit_points,
        "hp_ability": character.hp_ability,
        "hp_adjustment": character.hp_adjustment,
        "initiative_adjustment": character.initiative_adjustment,
        "proficiency_bonus_adjustment": character.proficiency_bonus_adjustment,
        "max_hp": character.max_hp,
        "hp_calculation": calculation(
            character.max_hp,
            character.rolled_hit_points,
            [
                {
                    "label": f"{character.hp_ability.title()} modifier × level",
                    "value": hp_modifier * character.level,
                    "formula": f"{hp_modifier} × {character.level}",
                    "source": "ability",
                },
                {
                    "label": "Custom modifier",
                    "value": character.hp_adjustment,
                    "source": "override",
                },
            ],
        ),
        "current_hp": character.current_hp,
        "temporary_hp": character.temporary_hp,
        "initiative": calculation(
            character.initiative_bonus,
            character.ability_modifier("dexterity"),
            [
                {
                    "label": "Half proficiency",
                    "value": initiative_half,
                    "source": "feature",
                },
                {
                    "label": "Custom modifier",
                    "value": character.initiative_adjustment,
                    "source": "override",
                },
            ],
        ),
        "proficiency_bonus": character.proficiency_bonus,
        "proficiency_bonus_calculation": calculation(
            character.proficiency_bonus,
            base_proficiency,
            [
                {
                    "label": "Level progression",
                    "value": base_proficiency,
                    "source": "rules",
                },
                {
                    "label": "Custom modifier",
                    "value": character.proficiency_bonus_adjustment,
                    "source": "override",
                },
            ],
        ),
        "jack_of_all_trades": character.jack_of_all_trades,
        "remarkable_athlete": character.remarkable_athlete,
        "abilities": {
            ability: {
                "score": character.ability_score(ability),
                "raw": getattr(character, ability),
                "ancestry_bonus": int(character.ability_bonuses.get(ability, 0)),
                "background_bonus": int(
                    character.background_ability_bonuses.get(ability, 0)
                ),
                "score_adjustment": int(
                    character.ability_score_adjustments.get(ability, 0)
                ),
                "modifier": character.ability_modifier(ability),
                "check_bonus": character.ability_check(ability),
                "check_formula": calculation(
                    character.ability_check(ability),
                    character.ability_modifier(ability),
                    [
                        {
                            "label": "Half proficiency",
                            "value": character.half_proficiency(ability, "none"),
                            "source": "feature",
                        }
                    ],
                ),
                "formula": calculation(
                    character.ability_score(ability),
                    getattr(character, ability),
                    [
                        {
                            "label": "Ancestry modifier",
                            "value": int(character.ability_bonuses.get(ability, 0)),
                            "source": "ancestry",
                        },
                        {
                            "label": "Background modifier",
                            "value": int(
                                character.background_ability_bonuses.get(ability, 0)
                            ),
                            "source": "background",
                        },
                        {
                            "label": "Custom modifier",
                            "value": int(
                                character.ability_score_adjustments.get(ability, 0)
                            ),
                            "source": "override",
                        },
                    ],
                ),
            }
            for ability in ABILITIES
        },
        "saves": {
            ability: {
                "proficiency": character.save_proficiencies.get(ability, "none"),
                "adjustment": int(character.save_adjustments.get(ability, 0)),
                "bonus": character.saving_throw(ability),
                "formula": calculation(
                    character.saving_throw(ability),
                    character.ability_modifier(ability),
                    [
                        {
                            "label": "Proficiency bonus",
                            "value": character.proficiency_bonus
                            if character.save_proficiencies.get(ability) == "proficient"
                            else 0,
                            "source": "proficiency",
                        },
                        {
                            "label": "Custom modifier",
                            "value": int(character.save_adjustments.get(ability, 0)),
                            "source": "override",
                        },
                    ],
                ),
            }
            for ability in ABILITIES
        },
        "skills": {
            skill: {
                "ability": ability,
                "proficiency": character.skill_proficiencies.get(skill, "none"),
                "adjustment": int(character.skill_adjustments.get(skill, 0)),
                "bonus": character.skill_bonus(skill, ability),
                "formula": calculation(
                    character.skill_bonus(skill, ability),
                    character.ability_modifier(ability),
                    [
                        {
                            "label": "Proficiency contribution",
                            "value": character.skill_bonus(skill, ability)
                            - character.ability_modifier(ability)
                            - int(character.skill_adjustments.get(skill, 0)),
                            "source": "proficiency",
                        },
                        {
                            "label": "Custom modifier",
                            "value": int(character.skill_adjustments.get(skill, 0)),
                            "source": "override",
                        },
                    ],
                ),
            }
            for skill, ability in SKILL_ABILITIES.items()
        },
    }


def character_data(
    character: Character, viewing_context: CampaignContext | None = None
) -> dict[str, object]:
    return {
        "id": character.pk,
        "context_id": character.context_id,
        "name": character.name,
        "portrait_url": character.portrait.url if character.portrait else None,
        "kind": character.kind,
        "is_player_character": character.is_player_character,
        "is_active": character.is_active,
        "race": character.race,
        "class": character.character_class,
        "experience": character.experience,
        "sheet": character_sheet_data(character),
        "money": money_data(character),
    }


def party_money(campaign: Campaign) -> dict[str, int | str]:
    totals: dict[str, int | str] = {
        "cp": 0,
        "sp": 0,
        "ep": 0,
        "gp": 0,
        "pp": 0,
    }
    rows = (
        MoneyEntry.objects.filter(
            account__character__campaign=campaign,
            account__character__is_active=True,
            account__character__kind=Character.Kind.PC,
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


def coin_amounts(
    amounts: dict[str, int],
) -> dict[MoneyEntry.Denomination, int]:
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


def can_act_for(context: CampaignContext, character: Character) -> bool:
    return context.kind == CampaignContext.Kind.GM or is_character_owner(
        context, character
    )


def transaction_data(
    posted: MoneyTransaction | ExperienceTransaction,
) -> dict[str, object]:
    return {
        "id": posted.pk,
        "ledger": posted._meta.model_name.removesuffix("transaction"),
        "ledger_label": str(posted._meta.verbose_name),
        "description": posted.description,
        "created_at": posted.occurred_at.isoformat(),
        "occurred_at": posted.occurred_at.isoformat(),
        "campaign_date": posted.campaign_date,
        "created_by_id": posted.created_by_id,
        "actor": (
            actor_name(posted.created_by.user)
            if posted.created_by_id
            else posted.actor_username or None
        ),
    }


def actor_name(user) -> str:
    return getattr(user, "name", "") or user.get_username()


def history_data(posted) -> dict[str, object]:
    data = transaction_data(posted)
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
    "money": MoneyTransaction,
    "experience": ExperienceTransaction,
}


def transaction_queryset(model, campaign: Campaign):
    entry_model = model._meta.get_field("entries").related_model
    entries = entry_model.objects.select_related("account__character")
    return (
        model.objects.filter(campaign=campaign)
        .select_related("created_by__user")
        .prefetch_related(Prefetch("entries", queryset=entries))
    )


def money_transfer_create(request, context_id: int, payload: MoneyTransferCreate):
    context = context_access(request, context_id)
    source = (
        character_for_context(context, payload.from_character_id)
        if payload.from_character_id
        else None
    )
    destination = (
        character_for_context(context, payload.to_character_id)
        if payload.to_character_id
        else None
    )
    if source is None and destination is None:
        raise HttpError(422, "A money transfer needs a source or destination.")
    if context.kind != CampaignContext.Kind.GM and (
        source is None or not can_act_for(context, source)
    ):
        raise HttpError(
            403, "Players may only transfer money from their own character."
        )
    amounts = coin_amounts(payload.amounts)
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
        raise unprocessable(error) from error
    notify_campaign_changed(context.campaign_id)
    return 201, transaction_data(posted)


def money_exchange_create(request, context_id: int, payload: MoneyExchangeCreate):
    context = context_access(request, context_id)
    character = character_for_context(context, payload.character_id)
    if not can_act_for(context, character):
        raise HttpError(403, "Players may only exchange their own coins.")
    try:
        posted = exchange_coins(
            character=character,
            given=coin_amounts(payload.given),
            received=coin_amounts(payload.received),
            description=payload.description,
        )
        posted.created_by = context
        posted.save(update_fields=("created_by",))
    except DjangoValidationError as error:
        raise unprocessable(error) from error
    notify_campaign_changed(context.campaign_id)
    return 201, transaction_data(posted)


def shared_xp_award_create(request, context_id: int, payload: SharedXpAwardCreate):
    context = context_access(request, context_id)
    gm_context(context)
    try:
        _, posted = context.campaign.award_shared_experience(
            payload.amount,
            description=payload.description,
            created_by=context,
            return_transaction=True,
        )
    except DjangoValidationError as error:
        raise unprocessable(error) from error
    notify_campaign_changed(context.campaign_id)
    return 201, transaction_data(posted)


def transaction_reverse(
    request,
    context_id: int,
    ledger: Literal["money", "experience"],
    transaction_id: int,
):
    context = context_access(request, context_id)
    model = TRANSACTION_MODELS[ledger]
    original = get_object_or_404(model, pk=transaction_id, campaign=context.campaign)
    latest = (
        model.objects.filter(campaign=context.campaign)
        .order_by("-occurred_at", "-pk")
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
        raise unprocessable(error) from error
    notify_campaign_changed(context.campaign_id)
    return history_data(reversed_posted)


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
