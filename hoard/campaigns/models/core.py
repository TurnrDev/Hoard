from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

if TYPE_CHECKING:
    from hoard.campaigns.models.experience import ExperienceAccount
    from hoard.campaigns.models.money import MoneyAccount, MoneyTransaction
    from hoard.campaigns.services.actions import CoinAmounts


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

    def money_system_account(self) -> MoneyAccount:
        from ..services.ledger import system_account
        from .money import MoneyAccount

        return system_account(MoneyAccount, self)

    def experience_system_account(self) -> ExperienceAccount:
        from ..services.ledger import system_account
        from .experience import ExperienceAccount

        return system_account(ExperienceAccount, self)

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


@dataclass(frozen=True)
class MoneyBalance:
    copper: int = 0
    silver: int = 0
    electrum: int = 0
    gold: int = 0
    platinum: int = 0

    @property
    def gold_value(self) -> Decimal:
        return (
            Decimal(self.copper) / Decimal(100)
            + Decimal(self.silver) / Decimal(10)
            + Decimal(self.electrum) / Decimal(2)
            + Decimal(self.gold)
            + Decimal(self.platinum) * Decimal(10)
        )


class Character(models.Model):
    campaign_id: int
    context_id: int | None

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="characters"
    )
    context = models.OneToOneField(
        CampaignContext,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="character",
    )

    class Kind(models.TextChoices):
        PC = "pc", "Player character"
        NPC = "npc", "Non-player character"

    kind = models.CharField(max_length=3, choices=Kind.choices, default=Kind.PC)
    is_active = models.BooleanField("Is Active", default=False)
    name = models.CharField("Character Name", max_length=200)
    portrait = models.FileField(upload_to="character-portraits/", blank=True)
    race = models.CharField(max_length=100, blank=True)
    character_class = models.CharField("Class", max_length=100, blank=True)
    rolled_hit_points = models.PositiveIntegerField("Rolled Hit Points", default=1)
    current_hp = models.PositiveIntegerField("Current HP", default=1)
    temporary_hp = models.PositiveIntegerField("Temporary HP", default=0)
    hp_ability = models.CharField(max_length=20, default="constitution")
    hp_adjustment = models.SmallIntegerField(default=0)
    initiative_adjustment = models.SmallIntegerField(default=0)
    proficiency_bonus_adjustment = models.SmallIntegerField(default=0)
    ability_bonuses = models.JSONField(default=dict, blank=True)
    background_ability_bonuses = models.JSONField(default=dict, blank=True)
    ability_score_adjustments = models.JSONField(default=dict, blank=True)
    skill_proficiencies = models.JSONField(default=dict, blank=True)
    skill_adjustments = models.JSONField(default=dict, blank=True)
    save_proficiencies = models.JSONField(default=dict, blank=True)
    save_adjustments = models.JSONField(default=dict, blank=True)
    jack_of_all_trades = models.BooleanField(default=False)
    remarkable_athlete = models.BooleanField(default=False)
    strength = models.PositiveSmallIntegerField(default=10)
    dexterity = models.PositiveSmallIntegerField(default=10)
    constitution = models.PositiveSmallIntegerField(default=10)
    intelligence = models.PositiveSmallIntegerField(default=10)
    wisdom = models.PositiveSmallIntegerField(default=10)
    charisma = models.PositiveSmallIntegerField(default=10)

    def clean(self) -> None:
        super().clean()
        if self.context_id and self.context.campaign_id != self.campaign_id:
            raise ValidationError(
                {"context": "A character context must belong to the same campaign."}
            )
        if self.context_id and self.context.kind != CampaignContext.Kind.PC:
            raise ValidationError({"context": "Only a PC context may own a character."})
        if self.kind == self.Kind.NPC and self.context_id:
            raise ValidationError(
                {"context": "NPCs cannot belong to a player context."}
            )
        if self.hp_ability not in ABILITY_NAMES:
            raise ValidationError({"hp_ability": "Choose a valid ability."})

        validate_stat_map(
            "ability_bonuses",
            self.ability_bonuses,
            ABILITY_NAMES,
            minimum=-30,
            maximum=30,
        )
        validate_stat_map(
            "background_ability_bonuses",
            self.background_ability_bonuses,
            ABILITY_NAMES,
            minimum=-30,
            maximum=30,
        )
        validate_stat_map(
            "ability_score_adjustments",
            self.ability_score_adjustments,
            ABILITY_NAMES,
            minimum=-30,
            maximum=30,
        )
        validate_stat_map(
            "skill_adjustments",
            self.skill_adjustments,
            SKILL_NAMES,
            minimum=-99,
            maximum=99,
        )
        validate_stat_map(
            "save_adjustments",
            self.save_adjustments,
            ABILITY_NAMES,
            minimum=-99,
            maximum=99,
        )
        validate_stat_map(
            "skill_proficiencies",
            self.skill_proficiencies,
            SKILL_NAMES,
            {"none", "proficient", "expertise"},
        )
        validate_stat_map(
            "save_proficiencies",
            self.save_proficiencies,
            ABILITY_NAMES,
            {"none", "proficient"},
        )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_player_character(self) -> bool:
        return self.kind == self.Kind.PC

    @staticmethod
    def level_for_experience(experience: int) -> int:
        return max(
            level
            for level, threshold in enumerate(XP_LEVEL_THRESHOLDS, start=1)
            if experience >= threshold
        )

    @property
    def level(self) -> int:
        return self.campaign.level

    @property
    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4 + self.proficiency_bonus_adjustment

    def ability_score(self, ability: str) -> int:
        return (
            getattr(self, ability)
            + int(self.ability_bonuses.get(ability, 0))
            + int(self.background_ability_bonuses.get(ability, 0))
            + int(self.ability_score_adjustments.get(ability, 0))
        )

    def ability_modifier(self, ability: str) -> int:
        return (self.ability_score(ability) - 10) // 2

    def half_proficiency(self, ability: str, proficiency: str) -> int:
        if proficiency != "none":
            return 0
        down = self.proficiency_bonus // 2 if self.jack_of_all_trades else 0
        up = (
            (self.proficiency_bonus + 1) // 2
            if self.remarkable_athlete
            and ability in {"strength", "dexterity", "constitution"}
            else 0
        )
        return max(down, up)

    def saving_throw(self, ability: str) -> int:
        proficiency = self.save_proficiencies.get(ability, "none")
        contribution = self.proficiency_bonus if proficiency == "proficient" else 0
        return (
            self.ability_modifier(ability)
            + contribution
            + int(self.save_adjustments.get(ability, 0))
        )

    def ability_check(self, ability: str) -> int:
        return self.ability_modifier(ability) + self.half_proficiency(ability, "none")

    def skill_bonus(self, skill: str, ability: str) -> int:
        proficiency = self.skill_proficiencies.get(skill, "none")
        contribution = {
            "proficient": self.proficiency_bonus,
            "expertise": self.proficiency_bonus * 2,
        }.get(proficiency, self.half_proficiency(ability, proficiency))
        return (
            self.ability_modifier(ability)
            + contribution
            + int(self.skill_adjustments.get(skill, 0))
        )

    @property
    def max_hp(self) -> int:
        return max(
            1,
            self.rolled_hit_points
            + self.ability_modifier(self.hp_ability) * self.level
            + self.hp_adjustment,
        )

    @property
    def initiative_bonus(self) -> int:
        return (
            self.ability_modifier("dexterity")
            + self.half_proficiency("dexterity", "none")
            + self.initiative_adjustment
        )

    @property
    def experience(self) -> int:
        from .experience import ExperienceEntry

        return (
            ExperienceEntry.objects.filter(account__character=self).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

    @property
    def money(self) -> MoneyBalance:
        from .money import MoneyEntry

        totals = defaultdict(int)
        for entry in (
            MoneyEntry.objects.filter(account__character=self)
            .values("denomination")
            .annotate(total=Sum("amount"))
        ):
            totals[entry["denomination"]] = entry["total"]
        return MoneyBalance(
            copper=totals[MoneyEntry.Denomination.COPPER],
            silver=totals[MoneyEntry.Denomination.SILVER],
            electrum=totals[MoneyEntry.Denomination.ELECTRUM],
            gold=totals[MoneyEntry.Denomination.GOLD],
            platinum=totals[MoneyEntry.Denomination.PLATINUM],
        )

    def activate(self) -> Character:
        from ..services.experience import activate_character

        return activate_character(self)

    def grant_coins(
        self, coins: CoinAmounts, description: str = ""
    ) -> MoneyTransaction:
        from ..services.actions import grant_coins

        return grant_coins(recipient=self, coins=coins, description=description)

    def spend_coins(
        self, coins: CoinAmounts, description: str = ""
    ) -> MoneyTransaction:
        from ..services.actions import spend_coins

        return spend_coins(spender=self, coins=coins, description=description)

    def exchange_coins(
        self, given: CoinAmounts, received: CoinAmounts, description: str = ""
    ) -> MoneyTransaction:
        from ..services.actions import exchange_coins

        return exchange_coins(
            character=self, given=given, received=received, description=description
        )

    def money_account(self) -> MoneyAccount:
        from ..services.ledger import character_account
        from .money import MoneyAccount

        return character_account(MoneyAccount, self)

    def experience_account(self) -> ExperienceAccount:
        from ..services.ledger import character_account
        from .experience import ExperienceAccount

        return character_account(ExperienceAccount, self)

    def __str__(self) -> str:
        return self.name
