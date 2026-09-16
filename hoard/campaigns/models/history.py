from __future__ import annotations

from django.conf import settings
from django.db import models

from .audit import CampaignDatedEvent


class HealthTransaction(CampaignDatedEvent):
    class Reason(models.TextChoices):
        DAMAGE = "damage", "Damage"
        HEALING = "healing", "Healing"
        TEMPORARY = "temporary", "Temporary HP"
        CORRECTION = "correction", "Correction"
        SHORT_REST = "short_rest", "Short rest"
        LONG_REST = "long_rest", "Long rest"

    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.PROTECT, related_name="health_history"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    current_hp_before = models.PositiveIntegerField()
    current_hp_after = models.PositiveIntegerField()
    temporary_hp_before = models.PositiveIntegerField()
    temporary_hp_after = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Health Change"
        verbose_name_plural = "Health Changes"


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
