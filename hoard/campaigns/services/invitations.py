from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    CampaignContext,
    CampaignInvitation,
    Character,
    CharacterHistory,
    InvitationEvent,
)
from .health import create_health_baseline
from .history import record_character_history


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_invitation(
    context: CampaignContext, email: str = ""
) -> tuple[CampaignInvitation, str]:
    token = secrets.token_urlsafe(32)
    invitation = CampaignInvitation.objects.create(
        campaign=context.campaign,
        created_by=context,
        token_digest=token_digest(token),
        delivery_email=email,
        expires_at=timezone.now() + timedelta(days=7),
    )
    InvitationEvent.objects.create(
        campaign=context.campaign,
        invitation=invitation,
        created_by=context,
        reason=InvitationEvent.Reason.CREATED,
    )
    return invitation, token


def invitation_for_token(token: str, *, lock: bool = False) -> CampaignInvitation:
    query = CampaignInvitation.objects.select_related("campaign", "created_by")
    if lock:
        query = query.select_for_update(of=("self",))
    invitation = query.filter(token_digest=token_digest(token)).first()
    if invitation is None:
        raise ValidationError("Invitation not found.")
    if invitation.revoked_at:
        raise ValidationError("This invitation was revoked.")
    if invitation.accepted_at:
        raise ValidationError("This invitation was already accepted.")
    if invitation.expires_at <= timezone.now():
        raise ValidationError("This invitation has expired.")
    return invitation


def accept_invitation(token: str, user) -> CampaignContext:
    with transaction.atomic():
        invitation = invitation_for_token(token, lock=True)
        if CampaignContext.objects.filter(
            campaign=invitation.campaign,
            user=user,
            kind=CampaignContext.Kind.PC,
        ).exists():
            raise ValidationError("You already have a player context in this campaign.")
        context = CampaignContext.objects.create(
            campaign=invitation.campaign, user=user, kind=CampaignContext.Kind.PC
        )
        character = Character.objects.create(
            campaign=invitation.campaign,
            context=context,
            name=user.get_username(),
            race="",
            character_class="",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            is_active=False,
            is_build_complete=False,
        )
        create_health_baseline(character, created_by=context)
        record_character_history(
            character,
            reason=CharacterHistory.Reason.CREATE,
            before=None,
            created_by=context,
            description="Created from campaign invitation",
        )
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save(update_fields=("accepted_at", "accepted_by"))
        InvitationEvent.objects.create(
            campaign=invitation.campaign,
            invitation=invitation,
            created_by=context,
            reason=InvitationEvent.Reason.ACCEPTED,
        )
        return context


def register_and_accept(token: str, username: str, email: str, password: str):
    user_model = get_user_model()
    if user_model.objects.filter(username=username).exists():
        raise ValidationError({"username": "That username already exists."})
    if email and user_model.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "That email already belongs to an account."})
    with transaction.atomic():
        user = user_model.objects.create_user(
            username=username, email=email, password=password
        )
        context = accept_invitation(token, user)
    return user, context
