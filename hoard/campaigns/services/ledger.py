from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    InventoryEntry,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
)

COPPER_VALUES = {
    MoneyEntry.Denomination.COPPER: 1,
    MoneyEntry.Denomination.SILVER: 10,
    MoneyEntry.Denomination.ELECTRUM: 50,
    MoneyEntry.Denomination.GOLD: 100,
    MoneyEntry.Denomination.PLATINUM: 1000,
}


def system_account(account_model, campaign):
    """Return the campaign's balancing system account for a ledger type."""
    return account_model.objects.get_or_create(campaign=campaign, is_system=True, defaults={'character': None})[0]


def character_account(account_model, character):
    """Return a character's account for a ledger type."""
    return account_model.objects.get_or_create(
        campaign=character.campaign,
        character=character,
        defaults={'is_system': False},
    )[0]


def _validate_campaign_scope(campaign, *objects):
    for obj in objects:
        if obj.campaign_id != campaign.id:
            raise ValidationError('Every supplied object must belong to the same campaign.')


def post_inventory_transaction(*, from_account, to_account, item, quantity, description=''):
    """Transfer a positive quantity of one item between two campaign accounts."""
    campaign = from_account.campaign
    _validate_campaign_scope(campaign, to_account, item)
    if quantity <= 0:
        raise ValidationError('Inventory quantities must be positive.')
    if from_account.pk == to_account.pk:
        raise ValidationError('Inventory transfers need different source and destination accounts.')
    with transaction.atomic():
        posted = InventoryTransaction.objects.create(campaign=campaign, description=description)
        InventoryEntry.objects.bulk_create([
            InventoryEntry(transaction=posted, account=from_account, item=item, amount=-quantity),
            InventoryEntry(transaction=posted, account=to_account, item=item, amount=quantity),
        ])
    return posted


def post_money_transaction(entries, *, description=''):
    """Post [(account, denomination, signed_amount), ...] when copper value balances."""
    entries = list(entries)
    if not entries:
        raise ValidationError('Money transactions need at least one entry.')
    campaign = entries[0][0].campaign
    total_value = 0
    for index, (account, denomination, amount) in enumerate(entries):
        if index:
            _validate_campaign_scope(campaign, account)
        if denomination not in COPPER_VALUES or not amount:
            raise ValidationError('Money entries need a denomination and non-zero amount.')
        total_value += COPPER_VALUES[denomination] * amount
    if total_value != 0:
        raise ValidationError('Money transactions must balance to zero in copper value.')
    with transaction.atomic():
        posted = MoneyTransaction.objects.create(campaign=campaign, description=description)
        MoneyEntry.objects.bulk_create([
            MoneyEntry(transaction=posted, account=account, denomination=denomination, amount=amount)
            for account, denomination, amount in entries
        ])
    return posted


def _entry_data(entry):
    values = {'amount': -entry.amount}
    if isinstance(entry, InventoryEntry):
        values['item'] = entry.item
    elif isinstance(entry, MoneyEntry):
        values['denomination'] = entry.denomination
    return values


def _reverse_entries(original, transaction_model, entry_model, *, description=''):
    with transaction.atomic():
        original = transaction_model.objects.select_for_update().get(pk=original.pk)
        if hasattr(original, 'reversal'):
            raise ValidationError('This transaction has already been reversed.')
        reverse = transaction_model.objects.create(
            campaign=original.campaign,
            description=description or f'Reversal of transaction {original.pk}',
            reversal_of=original,
        )
        entry_model.objects.bulk_create([
            entry_model(transaction=reverse, account=entry.account, **_entry_data(entry))
            for entry in original.entries.all()
        ])
        return reverse


def reverse_inventory_transaction(transaction_to_reverse, *, description=''):
    return _reverse_entries(transaction_to_reverse, InventoryTransaction, InventoryEntry, description=description)


def reverse_money_transaction(transaction_to_reverse, *, description=''):
    return _reverse_entries(transaction_to_reverse, MoneyTransaction, MoneyEntry, description=description)
