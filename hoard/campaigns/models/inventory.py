from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .ledger import ImmutableLedgerEntry, LedgerTransaction


class InventoryItem(models.Model):
    campaign_id: int | None
    created_by_id: int | None

    campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True, on_delete=models.CASCADE, related_name='inventory_items'
    )
    created_by = models.ForeignKey(
        'campaigns.Player', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_inventory_items'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    source_repository = models.URLField(blank=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_identifier = models.CharField(max_length=200, blank=True)
    source_data = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('campaign', 'name'),
                condition=Q(campaign__isnull=False),
                name='unique_inventory_item_name_per_campaign',
            ),
            models.UniqueConstraint(
                fields=('source_repository', 'source_system', 'source_identifier'),
                condition=Q(source_identifier__gt=''),
                name='unique_imported_inventory_item_source',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.created_by_id and (self.campaign_id is None or self.created_by.campaign_id != self.campaign_id):
            raise ValidationError({'created_by': 'Custom item creators must belong to the item campaign.'})

    @property
    def is_imported(self) -> bool:
        return bool(self.source_identifier)


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
