from django.db import models
from django.db.models import Q

from .ledger import ImmutableLedgerEntry, LedgerTransaction


class ExperienceAccount(models.Model):
    campaign_id: int
    character_id: int | None

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="experience_accounts",
    )
    character = models.OneToOneField(
        "campaigns.Character",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="experience_ledger_account",
    )
    is_system = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign",),
                condition=Q(is_system=True),
                name="one_system_experience_account_per_campaign",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_system=True, character__isnull=True)
                    | Q(is_system=False, character__isnull=False)
                ),
                name="experience_account_system_or_character",
            ),
        ]


class ExperienceTransaction(LedgerTransaction):
    reversal_of_id: int | None

    class Reason(models.TextChoices):
        SHARED_AWARD = "shared_award", "Shared award"
        BASELINE = "baseline", "Activation baseline"
        REVERSAL = "reversal", "Reversal"

    reason = models.CharField(max_length=20, choices=Reason.choices)
    requested_amount = models.PositiveIntegerField(default=0)
    discarded_amount = models.PositiveIntegerField(default=0)
    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )


class ExperienceEntry(ImmutableLedgerEntry):
    transaction_id: int
    account_id: int

    transaction = models.ForeignKey(
        ExperienceTransaction, on_delete=models.PROTECT, related_name="entries"
    )
    account = models.ForeignKey(
        ExperienceAccount, on_delete=models.PROTECT, related_name="entries"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount=0), name="experience_entry_nonzero_amount"
            )
        ]
