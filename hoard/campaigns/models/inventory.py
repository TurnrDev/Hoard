from __future__ import annotations

from django.db import models
from django.db.models import Q

from .ledger import ImmutableLedgerEntry, LedgerTransaction


class InventoryAccount(models.Model):
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="inventory_accounts",
    )
    character = models.OneToOneField(
        "campaigns.Character",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="inventory_ledger_account",
    )
    is_system = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_system=True),
                name="one_system_inventory_account_per_campaign",
            ),
            models.CheckConstraint(
                condition=Q(is_system=True, character__isnull=True)
                | Q(is_system=False, character__isnull=False),
                name="inventory_account_system_or_character",
            ),
        ]


class InventoryTransaction(LedgerTransaction):
    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )


class InventoryEntry(ImmutableLedgerEntry):
    transaction = models.ForeignKey(
        InventoryTransaction, on_delete=models.PROTECT, related_name="entries"
    )
    account = models.ForeignKey(
        InventoryAccount, on_delete=models.PROTECT, related_name="entries"
    )
    item = models.ForeignKey(
        "compendium.CompendiumEntry",
        on_delete=models.PROTECT,
        related_name="inventory_entries",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount=0), name="inventory_entry_nonzero_amount"
            )
        ]
