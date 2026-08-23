from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from .audit import CampaignDatedEvent


class LedgerTransaction(CampaignDatedEvent):
    description = models.TextField("Description", blank=True)

    class Meta:
        abstract = True

    @property
    def created_at(self):
        """Compatibility alias while clients migrate to occurred_at."""
        return self.occurred_at


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
