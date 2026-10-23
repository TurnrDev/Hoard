from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import Campaign, CampaignContext, Character, PartyExperienceAward


class Credentials(Schema):
    username: str
    password: str


api = NinjaAPI(title="Hoard API", version="0.2.1", auth=django_auth)


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

    if character is None:
        character_name = None
    elif not character.dicecloud_creature_id and character.name:
        character_name = character.name
    else:
        character_name = context.user.get_username()

    return {
        "id": context.pk,
        "active_context_id": context.pk,
        "campaign_id": context.campaign_id,
        "campaign_name": context.campaign.name,
        "kind": context.kind,
        "character_id": character.pk if character else None,
        "character_name": character_name,
    }


def dicecloud_projection(character: Character) -> dict[str, object] | None:
    if not character.dicecloud_creature_id:
        return None

    from .services.dicecloud import DiceCloudUnavailable, load_creature

    try:
        return load_creature(character.dicecloud_creature_id)
    except DiceCloudUnavailable as error:
        return {"unavailable": True, "error": str(error)}


def character_data(
    character: Character,
    viewing_context: CampaignContext | None = None,
    projection: dict[str, object] | None = None,
) -> dict[str, object]:
    if projection is None:
        projection = dicecloud_projection(character)
    if character.dicecloud_creature_id:
        fallback_name = (
            character.context.user.get_username()
            if character.context_id is not None
            else f"Linked player {character.pk}"
        )
    else:
        fallback_name = character.name or (
            character.context.user.get_username()
            if character.context_id is not None
            else f"Unlinked player {character.pk}"
        )
    name = projection.get("name", fallback_name) if projection else fallback_name
    image_url = projection.get("image_url") if projection else None
    details = projection.get("details", {}) if projection else {}
    return {
        "id": character.pk,
        "context_id": character.context_id,
        "name": name,
        "portrait_url": image_url,
        "is_player_character": True,
        "is_active": character.is_active,
        "is_connected": bool(character.dicecloud_creature_id),
        "dicecloud_creature_id": character.dicecloud_creature_id or None,
        "current_hp": None if character.dicecloud_creature_id else character.current_hp,
        "max_hp": None if character.dicecloud_creature_id else character.max_hp,
        "profile": projection,
        "race": details.get("race", "") if isinstance(details, dict) else "",
        "class": details.get("class", "") if isinstance(details, dict) else "",
    }


def party_money(
    campaign: Campaign, projections: dict[int, dict[str, object] | None]
) -> dict[str, int | str]:
    totals: dict[str, int | str] = {
        "cp": 0,
        "sp": 0,
        "ep": 0,
        "gp": 0,
        "pp": 0,
    }
    for character_id, projection in projections.items():
        if projection is None:
            continue
        character = campaign.characters.get(pk=character_id)
        if not character.is_active:
            continue
        currency = projection.get("currency")
        if not isinstance(currency, dict):
            continue
        for denomination in ("cp", "sp", "ep", "gp", "pp"):
            value = currency.get(denomination, 0)
            if isinstance(value, int):
                totals[denomination] += value
    totals["gold_value"] = str(
        Decimal(totals["cp"]) / 100
        + Decimal(totals["sp"]) / 10
        + Decimal(totals["ep"]) / 2
        + Decimal(totals["gp"])
        + Decimal(totals["pp"]) * 10
    )
    return totals


def party_experience_award_data(award: PartyExperienceAward) -> dict[str, object]:
    return {
        "id": award.pk,
        "amount": award.amount,
        "recipient_count": award.recipient_count,
        "awarded_per_player": award.awarded_per_player,
        "discarded_amount": award.discarded_amount,
        "reason": award.reason,
        "description": award.description,
        "occurred_at": award.occurred_at.isoformat(),
        "campaign_date": award.campaign_date,
        "actor": (
            award.created_by.user.get_username()
            if award.created_by_id
            else award.actor_username or None
        ),
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
