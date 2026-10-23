from __future__ import annotations

from django.conf import settings
from django.db import models

from .audit import CampaignDatedEvent


class MembershipEvent(CampaignDatedEvent):
    class Reason(models.TextChoices):
        DEACTIVATED = "deactivated", "Deactivated"

    subject = models.ForeignKey(
        "campaigns.CampaignContext",
        null=True,
        on_delete=models.SET_NULL,
        related_name="membership_events",
    )
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Membership Change"
        verbose_name_plural = "Membership Changes"
