from django.db import models
from django.db.models import Q


class Encounter(models.Model):
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="encounters",
    )
    is_active = models.BooleanField(default=True)
    current_combatant = models.ForeignKey(
        "campaigns.EncounterCombatant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_active=True),
                name="one_active_encounter_per_campaign",
            )
        ]


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
    position = models.PositiveIntegerField(default=0)
    current_hp = models.PositiveIntegerField(null=True, blank=True)
    max_hp = models.PositiveIntegerField(null=True, blank=True)
    show_hp_numbers = models.BooleanField(default=False)

    class Meta:
        ordering = ("position", "pk")

    @property
    def display_name(self) -> str:
        if self.character_id:
            return self.character.name

        return self.name
