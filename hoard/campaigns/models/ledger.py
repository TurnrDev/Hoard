from django.core.exceptions import ValidationError
from django.db import models


class LedgerTransaction(models.Model):
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ImmutableLedgerEntry(models.Model):
    amount = models.IntegerField()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Posted ledger entries are immutable; post a reversal instead.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Posted ledger entries are immutable; post a reversal instead.')
