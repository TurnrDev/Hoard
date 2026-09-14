from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .audit import CampaignDatedEvent


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
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_active=True),
                name="one_active_encounter_per_campaign",
            ),
        ]

    def finish(self) -> None:
        if not self.is_active:
            return

        self.is_active = False
        self.ended_at = timezone.now()
        self.save(update_fields=("is_active", "ended_at"))

    def __str__(self) -> str:
        return f"{self.campaign} encounter {self.pk}"


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
    creature_entry = models.ForeignKey(
        "compendium.CompendiumEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="encounter_combatants",
    )
    name = models.CharField(max_length=200, blank=True)
    initiative = models.SmallIntegerField(default=0)
    current_hp = models.IntegerField(null=True, blank=True)
    max_hp = models.PositiveIntegerField(null=True, blank=True)
    show_hp_bar = models.BooleanField(default=False)
    show_hp_numbers = models.BooleanField(default=False)

    class Meta:
        ordering = ("-initiative", "pk")
        constraints = [
            models.CheckConstraint(
                condition=Q(current_hp__isnull=True) | Q(current_hp__gte=0),
                name="encounter_combatant_current_hp_nonnegative",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if self.character_id:
            if self.character.campaign_id != self.encounter.campaign_id:
                raise ValidationError(
                    {"character": "A combatant must belong to the encounter campaign."}
                )

        if self.creature_entry_id:
            if self.creature_entry.kind != "monster":
                raise ValidationError(
                    {"creature_entry": "A combatant may only link to a creature entry."}
                )

            repository_campaign_id = self.creature_entry.source.repository.campaign_id
            if repository_campaign_id not in {None, self.encounter.campaign_id}:
                raise ValidationError(
                    {
                        "creature_entry": (
                            "A campaign-local creature must belong to the encounter campaign."
                        )
                    }
                )

        if (
            not self.character_id
            and not self.creature_entry_id
            and not self.name.strip()
        ):
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

        if self.name.strip():
            return self.name.strip()

        return self.creature_entry.name

    @property
    def health(self) -> tuple[int | None, int | None]:
        if self.character_id:
            return self.character.current_hp, self.character.max_hp

        return self.current_hp, self.max_hp

    def __str__(self) -> str:
        return f"{self.display_name} in {self.encounter}"


class ConditionDetails(models.Model):
    class Identifier(models.TextChoices):
        BLINDED = "blinded", "Blinded"
        CHARMED = "charmed", "Charmed"
        DEAFENED = "deafened", "Deafened"
        EXHAUSTION = "exhaustion", "Exhaustion"
        FRIGHTENED = "frightened", "Frightened"
        GRAPPLED = "grappled", "Grappled"
        INCAPACITATED = "incapacitated", "Incapacitated"
        INVISIBLE = "invisible", "Invisible"
        PARALYZED = "paralyzed", "Paralyzed"
        PETRIFIED = "petrified", "Petrified"
        POISONED = "poisoned", "Poisoned"
        PRONE = "prone", "Prone"
        RESTRAINED = "restrained", "Restrained"
        STUNNED = "stunned", "Stunned"
        UNCONSCIOUS = "unconscious", "Unconscious"
        PACIFY = "pacify", "Pacify"

    identifier = models.CharField(max_length=20, choices=Identifier.choices)
    source = models.CharField(max_length=200, blank=True)
    duration = models.CharField(max_length=200, blank=True)
    exhaustion_level = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ("identifier", "pk")

    def clean(self) -> None:
        super().clean()

        if self.identifier == self.Identifier.EXHAUSTION:
            if self.exhaustion_level is None or not 1 <= self.exhaustion_level <= 6:
                raise ValidationError(
                    {"exhaustion_level": "Exhaustion requires a level from 1 to 6."}
                )
        elif self.exhaustion_level is not None:
            raise ValidationError(
                {"exhaustion_level": "Only exhaustion may have an exhaustion level."}
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)


class CharacterCondition(ConditionDetails):
    """One effect imposing a condition that persists across encounters."""

    character = models.ForeignKey(
        "campaigns.Character",
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    class Meta(ConditionDetails.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("character", "identifier"),
                condition=Q(identifier=ConditionDetails.Identifier.EXHAUSTION),
                name="one_exhaustion_condition_per_character",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_identifier_display()} on {self.character}"


class CombatantCondition(ConditionDetails):
    """One effect imposing a condition on an encounter-only combatant."""

    combatant = models.ForeignKey(
        EncounterCombatant,
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    class Meta(ConditionDetails.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("combatant", "identifier"),
                condition=Q(identifier=ConditionDetails.Identifier.EXHAUSTION),
                name="one_exhaustion_condition_per_combatant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_identifier_display()} on {self.combatant}"


class ConditionEvent(CampaignDatedEvent):
    """Immutable campaign-dated history for a condition instance."""

    class Action(models.TextChoices):
        APPLIED = "applied", "Applied"
        UPDATED = "updated", "Updated"
        REMOVED = "removed", "Removed"

    character = models.ForeignKey(
        "campaigns.Character",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="condition_history",
    )
    encounter = models.ForeignKey(
        Encounter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="condition_events",
    )
    combatant = models.ForeignKey(
        EncounterCombatant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="condition_events",
    )
    condition_instance_id = models.PositiveBigIntegerField()
    target_name = models.CharField(max_length=200)
    identifier = models.CharField(
        max_length=20, choices=ConditionDetails.Identifier.choices
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ("-occurred_at", "-pk")
        verbose_name = "Condition Change"
        verbose_name_plural = "Condition Changes"

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.get_identifier_display()} on {self.target_name}"
