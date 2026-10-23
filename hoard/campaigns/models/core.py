from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

XP_LEVEL_THRESHOLDS = (
    0,
    300,
    900,
    2700,
    6500,
    14000,
    23000,
    34000,
    48000,
    64000,
    85000,
    100000,
    120000,
    140000,
    165000,
    195000,
    225000,
    265000,
    305000,
    355000,
)

ABILITY_NAMES = {
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
}
SKILL_NAMES = {
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
}


def validate_stat_map(
    field: str,
    values: object,
    allowed_keys: set[str],
    allowed_values: set[str] | None = None,
    minimum: int = -32768,
    maximum: int = 32767,
) -> None:
    if not isinstance(values, dict):
        raise ValidationError({field: "Must be an object."})

    unknown = set(values) - allowed_keys
    if unknown:
        raise ValidationError(
            {field: f"Unknown statistics: {', '.join(sorted(unknown))}."}
        )

    if allowed_values is None:
        invalid = [
            key
            for key, value in values.items()
            if type(value) is not int or not minimum <= value <= maximum
        ]
    else:
        invalid = [key for key, value in values.items() if value not in allowed_values]

    if invalid:
        raise ValidationError(
            {field: f"Invalid values for: {', '.join(sorted(invalid))}."}
        )


class Campaign(models.Model):
    name = models.CharField("Campaign Name", max_length=200)
    calendar_era_abbreviation = models.CharField(
        "Calendar Era Abbreviation", max_length=20, default="PD"
    )
    calendar_era_name = models.CharField(
        "Calendar Era Name", max_length=100, default="Powder Dynasty"
    )
    calendar_year = models.PositiveIntegerField("Calendar Year", default=81)
    calendar_day = models.PositiveSmallIntegerField("Calendar Day", default=137)
    shared_experience = models.PositiveIntegerField("Shared Experience", default=0)
    experience_recipient_count = models.PositiveSmallIntegerField(
        "XP Recipient Count", default=1
    )
    level = models.PositiveSmallIntegerField("Campaign Level", default=1)

    def adjust_calendar_day(self, amount: int) -> None:
        """Move the campaign calendar by a single non-zero number of days."""
        if amount not in (-1, 1):
            raise ValidationError("Calendar adjustments must be one day.")
        if amount == -1 and self.calendar_year == 1 and self.calendar_day == 1:
            raise ValidationError("The calendar cannot be before year 1, day 1.")
        if amount == 1 and self.calendar_day == 365:
            self.calendar_year += 1
            self.calendar_day = 1
        elif amount == -1 and self.calendar_day == 1:
            self.calendar_year -= 1
            self.calendar_day = 365
        else:
            self.calendar_day += amount

    def award_shared_experience(
        self,
        amount: int,
        description: str = "",
        dry_run: bool = False,
        created_by: CampaignContext | None = None,
        return_transaction: bool = False,
    ):
        from ..services.experience import award_shared_experience

        return award_shared_experience(
            self,
            amount,
            description=description,
            dry_run=dry_run,
            created_by=created_by,
            return_transaction=return_transaction,
        )

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.calendar_year < 1:
            raise ValidationError({"calendar_year": "Year must be at least 1."})
        if not 1 <= self.calendar_day <= 365:
            raise ValidationError({"calendar_day": "Day must be between 1 and 365."})
        if not self.calendar_era_abbreviation.strip():
            raise ValidationError({"calendar_era_abbreviation": "Era is required."})
        if not self.calendar_era_name.strip():
            raise ValidationError({"calendar_era_name": "Era name is required."})


class CampaignContext(models.Model):
    campaign_id: int
    user_id: int

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="contexts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campaign_contexts",
    )

    class Kind(models.TextChoices):
        GM = "gm", "Game master"
        PC = "pc", "Player character"

    kind = models.CharField(max_length=2, choices=Kind.choices)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign", "user", "kind"),
                name="unique_context_kind_per_user_per_campaign",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} as {self.get_kind_display()} in {self.campaign}"

    def clean(self) -> None:
        super().clean()
        if not self.pk:
            return
        original_kind = (
            type(self).objects.filter(pk=self.pk).values_list("kind", flat=True).first()
        )
        if original_kind is not None and original_kind != self.kind:
            raise ValidationError(
                {"kind": "A campaign context's role cannot be changed."}
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)


class Character(models.Model):
    """A local campaign link to a public DiceCloud creature, not a character sheet."""

    campaign_id: int
    context_id: int | None

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="characters"
    )
    context = models.OneToOneField(
        CampaignContext,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="character",
    )
    name = models.CharField(max_length=200, blank=True)
    current_hp = models.PositiveIntegerField(null=True, blank=True)
    max_hp = models.PositiveIntegerField(null=True, blank=True)
    dicecloud_creature_id = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField("Is Active", default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign", "dicecloud_creature_id"),
                condition=~models.Q(dicecloud_creature_id=""),
                name="unique_dicecloud_creature_per_campaign",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.context_id is not None:
            if self.context.campaign_id != self.campaign_id:
                raise ValidationError(
                    {"context": "A character context must belong to the same campaign."}
                )
            if self.context.kind != CampaignContext.Kind.PC:
                raise ValidationError(
                    {"context": "Only player contexts may have DiceCloud links."}
                )
        has_local_combat_fallback = (
            bool(self.name.strip())
            and self.current_hp is not None
            and self.max_hp is not None
        )
        if (
            self.is_active
            and not self.dicecloud_creature_id
            and not has_local_combat_fallback
        ):
            raise ValidationError(
                {
                    "is_active": (
                        "Connect DiceCloud or provide a local name and both HP values "
                        "before activating this player."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    @staticmethod
    def level_for_experience(experience: int) -> int:
        return max(
            level
            for level, threshold in enumerate(XP_LEVEL_THRESHOLDS, start=1)
            if experience >= threshold
        )

    def __str__(self) -> str:
        if self.context_id is not None:
            return self.context.user.get_username()
        if self.dicecloud_creature_id:
            return f"Linked player {self.pk}"
        return self.name or f"Unlinked player {self.pk}"
