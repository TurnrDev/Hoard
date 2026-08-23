from __future__ import annotations

from django.conf import settings
from django.db import models

from .audit import CampaignDatedEvent


class CampaignInvitation(models.Model):
    campaign = models.ForeignKey(
        "campaigns.Campaign", on_delete=models.CASCADE, related_name="invitations"
    )
    created_by = models.ForeignKey(
        "campaigns.CampaignContext",
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_invitations",
    )
    token_digest = models.CharField(max_length=64, unique=True)
    delivery_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_campaign_invitations",
    )


class InvitationEvent(CampaignDatedEvent):
    class Reason(models.TextChoices):
        CREATED = "created", "Created"
        RESENT = "resent", "Resent"
        REVOKED = "revoked", "Revoked"
        ACCEPTED = "accepted", "Accepted"

    invitation = models.ForeignKey(
        CampaignInvitation, on_delete=models.PROTECT, related_name="events"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
