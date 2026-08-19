from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class LedgerTransaction(models.Model):
    campaign_id: int
    created_by_id: int | None

    campaign = models.ForeignKey("campaigns.Campaign", on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        "campaigns.CampaignContext", null=True, blank=True, on_delete=models.SET_NULL
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ImmutableLedgerEntry(models.Model):
    amount = models.IntegerField()

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError(
                "Posted ledger entries are immutable; post a reversal instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError(
            "Posted ledger entries are immutable; post a reversal instead."
        )
