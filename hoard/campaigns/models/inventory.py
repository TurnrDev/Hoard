from __future__ import annotations

from django.db import models
from django.db.models import Q

from .ledger import ImmutableLedgerEntry, LedgerTransaction


class InventoryItem(models.Model):
    campaign_id: int

    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.CASCADE, related_name='inventory_items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('campaign', 'name'), name='unique_inventory_item_name_per_campaign')]

    def __str__(self) -> str:
        return self.name


class InventoryAccount(models.Model):
    campaign_id: int
    character_id: int | None

    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.CASCADE, related_name='inventory_accounts')
    character = models.OneToOneField('campaigns.Character', null=True, blank=True, on_delete=models.CASCADE, related_name='inventory_ledger_account')
    is_system = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('campaign',), condition=Q(is_system=True), name='one_system_inventory_account_per_campaign'),
            models.CheckConstraint(
                condition=(Q(is_system=True, character__isnull=True) | Q(is_system=False, character__isnull=False)),
                name='inventory_account_system_or_character',
            ),
        ]


class InventoryTransaction(LedgerTransaction):
    reversal_of_id: int | None

    reversal_of = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='reversal')


class InventoryEntry(ImmutableLedgerEntry):
    transaction_id: int
    account_id: int
    item_id: int

    transaction = models.ForeignKey(InventoryTransaction, on_delete=models.PROTECT, related_name='entries')
    account = models.ForeignKey(InventoryAccount, on_delete=models.PROTECT, related_name='entries')
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='entries')

    class Meta:
        constraints = [models.CheckConstraint(condition=~Q(amount=0), name='inventory_entry_nonzero_amount')]
