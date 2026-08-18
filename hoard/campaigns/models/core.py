from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

if TYPE_CHECKING:
    from hoard.campaigns.models.inventory import InventoryItem


class Campaign(models.Model):
    name = models.CharField(max_length=200)
    use_shared_exp = models.BooleanField(default=True)
    shared_experience = models.PositiveIntegerField(default=0)

    def inventory_system_account(self):
        from .inventory import InventoryAccount
        from ..services.ledger import system_account

        return system_account(InventoryAccount, self)

    def money_system_account(self):
        from .money import MoneyAccount
        from ..services.ledger import system_account

        return system_account(MoneyAccount, self)

    def experience_system_account(self):
        from .experience import ExperienceAccount
        from ..services.ledger import system_account

        return system_account(ExperienceAccount, self)

    def award_shared_experience(self, amount, description='', dry_run=False) -> int:
        from ..services.experience import award_shared_experience

        return award_shared_experience(self, amount, description=description, dry_run=dry_run)

    def __str__(self):
        return self.name


class Player(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='players')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaign_players')

    class Meta:
        constraints = [models.UniqueConstraint(fields=('campaign', 'user'), name='unique_player_per_campaign')]

    def __str__(self):
        return f'{self.user} in {self.campaign}'


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
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='characters')
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name='characters')
    is_active = models.BooleanField(default=False)
    name = models.CharField(max_length=200)
    race = models.CharField(max_length=100)
    character_class = models.CharField(max_length=100)
    strength = models.PositiveSmallIntegerField()
    dexterity = models.PositiveSmallIntegerField()
    constitution = models.PositiveSmallIntegerField()
    intelligence = models.PositiveSmallIntegerField()
    wisdom = models.PositiveSmallIntegerField()
    charisma = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('campaign', 'player'),
                condition=Q(is_active=True, player__isnull=False),
                name='one_active_character_per_player_per_campaign',
            ),
        ]

    def clean(self):
        super().clean()
        if self.player_id and self.player.campaign_id != self.campaign_id:
            raise ValidationError({'player': 'A player must belong to the same campaign as the character.'})

    @property
    def experience(self) -> int:
        from .experience import ExperienceEntry

        return ExperienceEntry.objects.filter(account__character=self).aggregate(total=Sum('amount'))['total'] or 0

    @property
    def money(self) -> MoneyBalance:
        from .money import MoneyEntry

        totals = defaultdict(int)
        for entry in MoneyEntry.objects.filter(account__character=self).values('denomination').annotate(total=Sum('amount')):
            totals[entry['denomination']] = entry['total']
        return MoneyBalance(
            copper=totals[MoneyEntry.Denomination.COPPER],
            silver=totals[MoneyEntry.Denomination.SILVER],
            electrum=totals[MoneyEntry.Denomination.ELECTRUM],
            gold=totals[MoneyEntry.Denomination.GOLD],
            platinum=totals[MoneyEntry.Denomination.PLATINUM],
        )

    @property
    def inventory(self) -> dict[InventoryItem, int]:
        from .inventory import InventoryEntry, InventoryItem

        rows = (
            InventoryEntry.objects.filter(account__character=self)
            .values('item_id')
            .annotate(total=Sum('amount'))
            .filter(total__gt=0)
        )
        items = InventoryItem.objects.in_bulk([row['item_id'] for row in rows])
        return {items[row['item_id']]: row['total'] for row in rows}

    def activate(self):
        from ..services.experience import activate_character

        return activate_character(self)

    def inventory_account(self):
        from .inventory import InventoryAccount
        from ..services.ledger import character_account

        return character_account(InventoryAccount, self)

    def money_account(self):
        from .money import MoneyAccount
        from ..services.ledger import character_account

        return character_account(MoneyAccount, self)

    def experience_account(self):
        from .experience import ExperienceAccount
        from ..services.ledger import character_account

        return character_account(ExperienceAccount, self)

    def __str__(self):
        return self.name
