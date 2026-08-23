from django.db import models
from django.db.models import Q

from .ledger import ImmutableLedgerEntry, LedgerTransaction


class MoneyAccount(models.Model):
    campaign_id: int
    character_id: int | None

    campaign = models.ForeignKey(
        "campaigns.Campaign", on_delete=models.CASCADE, related_name="money_accounts"
    )
    character = models.OneToOneField(
        "campaigns.Character",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="money_ledger_account",
    )
    is_system = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_system=True),
                name="one_system_money_account_per_campaign",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_system=True, character__isnull=True)
                    | Q(is_system=False, character__isnull=False)
                ),
                name="money_account_system_or_character",
            ),
        ]


class MoneyTransaction(LedgerTransaction):
    reversal_of_id: int | None

    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )

    class Meta:
        verbose_name = "Coins"
        verbose_name_plural = "Coins"


class MoneyEntry(ImmutableLedgerEntry):
    transaction_id: int
    account_id: int

    class Denomination(models.TextChoices):
        COPPER = "cp", "Copper"
        SILVER = "sp", "Silver"
        ELECTRUM = "ep", "Electrum"
        GOLD = "gp", "Gold"
        PLATINUM = "pp", "Platinum"

    transaction = models.ForeignKey(
        MoneyTransaction, on_delete=models.PROTECT, related_name="entries"
    )
    account = models.ForeignKey(
        MoneyAccount, on_delete=models.PROTECT, related_name="entries"
    )
    denomination = models.CharField(
        "Denomination", max_length=2, choices=Denomination.choices
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount=0), name="money_entry_nonzero_amount"
            )
        ]
