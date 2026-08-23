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


class CampaignLevelEvent(CampaignDatedEvent):
    previous_level = models.PositiveSmallIntegerField()
    next_level = models.PositiveSmallIntegerField()


class CalendarEvent(CampaignDatedEvent):
    before_era_abbreviation = models.CharField(max_length=20)
    before_year = models.PositiveIntegerField()
    before_day = models.PositiveSmallIntegerField()
    after_era_abbreviation = models.CharField(max_length=20)
    after_year = models.PositiveIntegerField()
    after_day = models.PositiveSmallIntegerField()


class MembershipEvent(CampaignDatedEvent):
    class Reason(models.TextChoices):
        ROLE_CHANGED = "role_changed", "Role changed"
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
