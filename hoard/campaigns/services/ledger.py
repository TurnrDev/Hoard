from __future__ import annotations

from typing import Protocol, TypeVar, cast

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    Campaign,
    Character,
    MoneyAccount,
    MoneyEntry,
    MoneyTransaction,
)


class CampaignScoped(Protocol):
    campaign_id: int


AccountT = TypeVar("AccountT", bound=CampaignScoped)
type MoneyEntryInput = tuple[MoneyAccount, MoneyEntry.Denomination, int]

COPPER_VALUES = {
    MoneyEntry.Denomination.COPPER: 1,
    MoneyEntry.Denomination.SILVER: 10,
    MoneyEntry.Denomination.ELECTRUM: 50,
    MoneyEntry.Denomination.GOLD: 100,
    MoneyEntry.Denomination.PLATINUM: 1000,
}


def system_account[AccountT: CampaignScoped](
    account_model: type[AccountT], campaign: Campaign
) -> AccountT:
    """Return the campaign's balancing system account for a ledger type."""
    account, _ = account_model.objects.get_or_create(
        campaign=campaign, is_system=True, defaults={"character": None}
    )
    return cast(AccountT, account)


def character_account[AccountT: CampaignScoped](
    account_model: type[AccountT], character: Character
) -> AccountT:
    """Return a character's account for a ledger type."""
    account, _ = account_model.objects.get_or_create(
        campaign=character.campaign,
        character=character,
        defaults={"is_system": False},
    )
    return cast(AccountT, account)


def validate_campaign_scope(campaign: Campaign, *objects: CampaignScoped) -> None:
    for obj in objects:
        if obj.campaign_id != campaign.id:
            raise ValidationError(
                "Every supplied object must belong to the same campaign."
            )


def post_money_transaction(
    entries: list[MoneyEntryInput], *, description: str = ""
) -> MoneyTransaction:
    """Post entries when their total copper value balances to zero."""
    entries = list(entries)
    if not entries:
        raise ValidationError("Money transactions need at least one entry.")
    campaign = entries[0][0].campaign
    total_value = 0
    for index, (account, denomination, amount) in enumerate(entries):
        if index:
            validate_campaign_scope(campaign, account)
        if denomination not in COPPER_VALUES or not amount:
            raise ValidationError(
                "Money entries need a denomination and non-zero amount."
            )
        total_value += COPPER_VALUES[denomination] * amount
    if total_value != 0:
        raise ValidationError(
            "Money transactions must balance to zero in copper value."
        )
    with transaction.atomic():
        posted = MoneyTransaction.objects.create(
            campaign=campaign, description=description
        )
        MoneyEntry.objects.bulk_create(
            [
                MoneyEntry(
                    transaction=posted,
                    account=account,
                    denomination=denomination,
                    amount=amount,
                )
                for account, denomination, amount in entries
            ]
        )
    return posted


def reverse_money_transaction(
    transaction_to_reverse: MoneyTransaction,
    *,
    description: str = "",
) -> MoneyTransaction:
    with transaction.atomic():
        original = MoneyTransaction.objects.select_for_update().get(
            pk=transaction_to_reverse.pk
        )
        if hasattr(original, "reversal"):
            raise ValidationError("This transaction has already been reversed.")
        reverse = MoneyTransaction.objects.create(
            campaign=original.campaign,
            description=description or f"Reversal of transaction {original.pk}",
            reversal_of=original,
        )
        MoneyEntry.objects.bulk_create(
            [
                MoneyEntry(
                    transaction=reverse,
                    account=entry.account,
                    denomination=entry.denomination,
                    amount=-entry.amount,
                )
                for entry in original.entries.all()
            ]
        )
        return reverse
