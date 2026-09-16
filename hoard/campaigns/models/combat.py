from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Encounter(models.Model):
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="encounters",
    )
    started_by = models.ForeignKey(
        "campaigns.CampaignContext",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="started_encounters",
    )
    is_active = models.BooleanField(default=True)
    current_combatant = models.ForeignKey(
        "campaigns.EncounterCombatant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    initiative_tie_choices = models.JSONField(default=dict, blank=True)
    initiative_tie_breaks = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_active=True),
                name="one_active_encounter_per_campaign",
            )
        ]

    def finish(self) -> None:
        if not self.is_active:
            return

        self.is_active = False
        self.ended_at = timezone.now()
        self.current_combatant = None
        self.initiative_tie_choices = {}
        self.initiative_tie_breaks = {}
        self.save(
            update_fields=(
                "is_active",
                "ended_at",
                "current_combatant",
                "initiative_tie_choices",
                "initiative_tie_breaks",
            )
        )


class EncounterCombatant(models.Model):
    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.CASCADE,
        related_name="combatants",
    )
    character = models.ForeignKey(
        "campaigns.Character",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="encounter_entries",
    )
    name = models.CharField(max_length=200, blank=True)
    initiative = models.SmallIntegerField(default=0)
    initiative_roll = models.PositiveSmallIntegerField(null=True, blank=True)
    initiative_modifier = models.SmallIntegerField(default=0)
    current_hp = models.IntegerField(null=True, blank=True)
    max_hp = models.PositiveIntegerField(null=True, blank=True)
    show_hp_numbers = models.BooleanField(default=False)

    class Meta:
        ordering = ("-initiative", "pk")
        constraints = [
            models.CheckConstraint(
                condition=Q(current_hp__isnull=True) | Q(current_hp__gte=0),
                name="encounter_combatant_current_hp_nonnegative",
            )
        ]

    def clean(self) -> None:
        super().clean()

        if self.character_id and self.character.campaign_id != self.encounter.campaign_id:
            raise ValidationError(
                {"character": "A combatant must belong to the encounter campaign."}
            )
        if not self.character_id and not self.name.strip():
            raise ValidationError(
                {"name": "An encounter-only combatant requires a name."}
            )
        if (self.current_hp is None) != (self.max_hp is None):
            raise ValidationError(
                "Generic current and maximum HP must either both be set or both be blank."
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        if self.character_id:
            return self.character.name

        return self.name.strip()

    @property
    def health(self) -> tuple[int | None, int | None]:
        if self.character_id:
            return self.character.current_hp, self.character.max_hp

        return self.current_hp, self.max_hp
