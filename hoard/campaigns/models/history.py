from __future__ import annotations

from django.conf import settings
from django.db import models

from .audit import CampaignDatedEvent


class CharacterHistory(CampaignDatedEvent):
    class Reason(models.TextChoices):
        CREATE = "create", "Created"
        IMPORT = "import", "Imported"
        EDIT = "edit", "Edited"
        OVERRIDE = "override", "Override"
        LEVEL_UP = "level_up", "Level up"

    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.PROTECT, related_name="history"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(blank=True)
    changes = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Character Modification"
        verbose_name_plural = "Character Modifications"


class CharacterNativeEvent(CampaignDatedEvent):
    """Immutable audit record for one authoritative native interpreter event."""

    character = models.ForeignKey(
        "campaigns.Character",
        on_delete=models.PROTECT,
        related_name="native_events",
    )
    event_name = models.CharField(max_length=300)
    payload = models.JSONField(default=dict)
    system_identifier = models.CharField(max_length=200)
    system_version = models.CharField(max_length=50, blank=True)
    system_checksum = models.CharField(max_length=64, blank=True)
    fired_events = models.JSONField(default=list)
    changes = models.JSONField(default=list)
    messages = models.JSONField(default=list)
    interface_actions = models.JSONField(default=list)
    delayed_effects = models.JSONField(default=list)
    unsupported = models.JSONField(default=list)

    class Meta:
        verbose_name = "Native Character Event"
        verbose_name_plural = "Native Character Events"


class HealthTransaction(CampaignDatedEvent):
    class Reason(models.TextChoices):
        BASELINE = "baseline", "Baseline"
        DAMAGE = "damage", "Damage"
        HEALING = "healing", "Healing"
        TEMPORARY = "temporary", "Temporary HP"
        CORRECTION = "correction", "Correction"

    character = models.ForeignKey(
        "campaigns.Character", on_delete=models.PROTECT, related_name="health_history"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    current_hp_delta = models.IntegerField(default=0)
    temporary_hp_delta = models.IntegerField(default=0)
    current_hp_before = models.IntegerField()
    current_hp_after = models.IntegerField()
    temporary_hp_before = models.IntegerField()
    temporary_hp_after = models.IntegerField()
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Health Change"
        verbose_name_plural = "Health Changes"


class CampaignLevelEvent(CampaignDatedEvent):
    previous_level = models.PositiveSmallIntegerField()
    next_level = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Level Up"
        verbose_name_plural = "Level Ups"


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
