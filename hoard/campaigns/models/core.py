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
    from hoard.campaigns.models.inventory import InventoryAccount, InventoryTransaction
    from hoard.campaigns.models.money import MoneyAccount, MoneyTransaction
    from hoard.campaigns.services.actions import CoinAmounts
    from hoard.compendium.models import CompendiumEntry


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


class Campaign(models.Model):
    name = models.CharField(max_length=200)
    calendar_era_abbreviation = models.CharField(max_length=20, default="PD")
    calendar_era_name = models.CharField(max_length=100, default="Powder Dynasty")
    calendar_year = models.PositiveIntegerField(default=81)
    calendar_day = models.PositiveSmallIntegerField(default=137)
    use_shared_exp = models.BooleanField(default=True)
    shared_experience = models.PositiveIntegerField(default=0)
    level = models.PositiveSmallIntegerField(default=1)
    compendium_sources = models.ManyToManyField(
        "compendium.CompendiumSource", blank=True, related_name="enabled_campaigns"
    )

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

    def inventory_system_account(self) -> InventoryAccount:
        from ..services.ledger import system_account
        from .inventory import InventoryAccount

        return system_account(InventoryAccount, self)

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign", "user", "kind"),
                name="unique_context_kind_per_user_per_campaign",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} as {self.get_kind_display()} in {self.campaign}"


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
    is_active = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_build_complete = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=200)
    race = models.CharField(max_length=100, blank=True)
    character_class = models.CharField(max_length=100, blank=True)
    background = models.CharField(max_length=100, blank=True)
    race_entry = models.ForeignKey(
        "compendium.CompendiumEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="race_characters",
    )
    background_entry = models.ForeignKey(
        "compendium.CompendiumEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="background_characters",
    )
    subrace_identifier = models.CharField(max_length=200, blank=True)
    subrace_name = models.CharField(max_length=200, blank=True)
    alignment = models.CharField(max_length=100, blank=True)
    personality_traits = models.TextField(blank=True)
    ideals = models.TextField(blank=True)
    bonds = models.TextField(blank=True)
    flaws = models.TextField(blank=True)
    about = models.TextField(blank=True)
    languages = models.JSONField(default=list, blank=True)
    equipment_proficiencies = models.JSONField(default=dict, blank=True)
    ability_bonuses = models.JSONField(default=dict, blank=True)
    ability_score_adjustments = models.JSONField(default=dict, blank=True)
    strength = models.PositiveSmallIntegerField()
    dexterity = models.PositiveSmallIntegerField()
    constitution = models.PositiveSmallIntegerField()
    intelligence = models.PositiveSmallIntegerField()
    wisdom = models.PositiveSmallIntegerField()
    charisma = models.PositiveSmallIntegerField()
    base_hp = models.PositiveSmallIntegerField(default=1)
    hp_ability = models.CharField(max_length=20, default="constitution")
    hp_adjustment = models.SmallIntegerField(default=0)
    current_hp = models.IntegerField(default=1)
    temporary_hp = models.IntegerField(default=0)
    base_ac = models.PositiveSmallIntegerField(default=10)
    ac_adjustment = models.SmallIntegerField(default=0)
    speed = models.CharField(max_length=100, blank=True)
    spell_slots = models.JSONField(default=dict, blank=True)
    proficiency_bonus_adjustment = models.SmallIntegerField(default=0)
    strength_modifier_adjustment = models.SmallIntegerField(default=0)
    dexterity_modifier_adjustment = models.SmallIntegerField(default=0)
    constitution_modifier_adjustment = models.SmallIntegerField(default=0)
    intelligence_modifier_adjustment = models.SmallIntegerField(default=0)
    wisdom_modifier_adjustment = models.SmallIntegerField(default=0)
    charisma_modifier_adjustment = models.SmallIntegerField(default=0)
    strength_save_proficient = models.BooleanField(default=False)
    dexterity_save_proficient = models.BooleanField(default=False)
    constitution_save_proficient = models.BooleanField(default=False)
    intelligence_save_proficient = models.BooleanField(default=False)
    wisdom_save_proficient = models.BooleanField(default=False)
    charisma_save_proficient = models.BooleanField(default=False)
    strength_save_adjustment = models.SmallIntegerField(default=0)
    dexterity_save_adjustment = models.SmallIntegerField(default=0)
    constitution_save_adjustment = models.SmallIntegerField(default=0)
    intelligence_save_adjustment = models.SmallIntegerField(default=0)
    wisdom_save_adjustment = models.SmallIntegerField(default=0)
    charisma_save_adjustment = models.SmallIntegerField(default=0)
    skill_proficiencies = models.JSONField(default=dict, blank=True)
    npc_level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = []

    def clean(self) -> None:
        super().clean()
        if self.context_id and self.context.campaign_id != self.campaign_id:
            raise ValidationError(
                {"context": "A character context must belong to the same campaign."}
            )
        if self.context_id and self.context.kind != CampaignContext.Kind.PC:
            raise ValidationError({"context": "Only a PC context may own a character."})

    @property
    def is_player_character(self) -> bool:
        return self.context_id is not None

    @property
    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4 + self.proficiency_bonus_adjustment

    @staticmethod
    def level_for_experience(experience: int) -> int:
        return max(
            level
            for level, threshold in enumerate(XP_LEVEL_THRESHOLDS, start=1)
            if experience >= threshold
        )

    @property
    def level(self) -> int:
        return self.campaign.level if self.is_player_character else self.npc_level

    @property
    def max_hp(self) -> int:
        return max(
            1,
            self.base_hp
            + self.ability_modifier(self.hp_ability) * self.level
            + self.hp_adjustment,
        )

    def ability_score(self, ability: str) -> int:
        return (
            getattr(self, ability)
            + int(self.ability_bonuses.get(ability, 0))
            + int(self.ability_score_adjustments.get(ability, 0))
        )

    def ability_modifier(self, ability: str) -> int:
        return (self.ability_score(ability) - 10) // 2 + getattr(
            self, f"{ability}_modifier_adjustment"
        )

    def saving_throw(self, ability: str) -> int:
        return (
            self.ability_modifier(ability)
            + getattr(self, f"{ability}_save_adjustment")
            + (
                self.proficiency_bonus
                if getattr(self, f"{ability}_save_proficient")
                else 0
            )
        )

    def skill_bonus(self, skill: str, ability: str) -> int:
        proficiency = self.skill_proficiencies.get(skill, "none")
        multiplier = {"none": 0, "half": 0.5, "proficient": 1, "expertise": 2}.get(
            proficiency, 0
        )
        return self.ability_modifier(ability) + int(self.proficiency_bonus * multiplier)

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

    @property
    def inventory(self) -> dict[CompendiumEntry, int]:
        from hoard.compendium.models import CompendiumEntry

        from .inventory import InventoryEntry

        rows = (
            InventoryEntry.objects.filter(account__character=self)
            .values("item_id")
            .annotate(total=Sum("amount"))
            .filter(total__gt=0)
        )
        items = CompendiumEntry.objects.in_bulk([row["item_id"] for row in rows])
        return {items[row["item_id"]]: row["total"] for row in rows}

    def activate(self) -> Character:
        from ..services.experience import activate_character

        return activate_character(self)

    def grant_loot(
        self, item: CompendiumEntry, quantity: int, description: str = ""
    ) -> InventoryTransaction:
        from ..services.actions import grant_loot

        return grant_loot(
            recipient=self, item=item, quantity=quantity, description=description
        )

    def transfer_item(
        self,
        recipient: Character,
        item: CompendiumEntry,
        quantity: int,
        description: str = "",
    ) -> InventoryTransaction:
        from ..services.actions import transfer_item

        return transfer_item(
            source=self,
            recipient=recipient,
            item=item,
            quantity=quantity,
            description=description,
        )

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

    def inventory_account(self) -> InventoryAccount:
        from ..services.ledger import character_account
        from .inventory import InventoryAccount

        return character_account(InventoryAccount, self)

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
