from __future__ import annotations

from collections.abc import Mapping

from django.core.exceptions import ValidationError

from hoard.compendium.models import CompendiumEntry

from ..models import (
    Character,
    ExperienceTransaction,
    InventoryTransaction,
    MoneyEntry,
    MoneyTransaction,
)
from .experience import reverse_experience_transaction
from .ledger import (
    COPPER_VALUES,
    post_inventory_transaction,
    post_money_transaction,
    reverse_inventory_transaction,
    reverse_money_transaction,
)

type CoinAmounts = Mapping[str | MoneyEntry.Denomination, int]
type LedgerTransaction = InventoryTransaction | MoneyTransaction | ExperienceTransaction


def _normalise_coins(coins: CoinAmounts) -> dict[MoneyEntry.Denomination, int]:
    amounts: dict[MoneyEntry.Denomination, int] = {}
    for denomination, amount in coins.items():
        try:
            normalised = MoneyEntry.Denomination(denomination)
        except ValueError as error:
            raise ValidationError(
                f"Unknown currency denomination: {denomination}."
            ) from error
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValidationError("Coin amounts must be positive integers.")
        amounts[normalised] = amounts.get(normalised, 0) + amount
    if not amounts:
        raise ValidationError("At least one coin amount is required.")
    return amounts


def _ensure_character_has_coins(
    character: Character, coins: Mapping[MoneyEntry.Denomination, int]
) -> None:
    balance = character.money
    available = {
        MoneyEntry.Denomination.COPPER: balance.copper,
        MoneyEntry.Denomination.SILVER: balance.silver,
        MoneyEntry.Denomination.ELECTRUM: balance.electrum,
        MoneyEntry.Denomination.GOLD: balance.gold,
        MoneyEntry.Denomination.PLATINUM: balance.platinum,
    }
    if any(amount > available[denomination] for denomination, amount in coins.items()):
        raise ValidationError(
            "A character cannot spend or exchange coins they do not hold."
        )


def grant_loot(
    *, recipient: Character, item: CompendiumEntry, quantity: int, description: str = ""
) -> InventoryTransaction:
    """Create items in the campaign system account and grant them to a character."""
    if not recipient.campaign.compendium_sources.filter(pk=item.source_id).exists():
        raise ValidationError("This item source is not enabled for the campaign.")
    return post_inventory_transaction(
        from_account=recipient.campaign.inventory_system_account(),
        to_account=recipient.inventory_account(),
        item=item,
        quantity=quantity,
        description=description,
    )


def transfer_item(
    *,
    source: Character,
    recipient: Character,
    item: CompendiumEntry,
    quantity: int,
    description: str = "",
) -> InventoryTransaction:
    """Transfer held inventory between two characters."""
    if quantity <= 0 or source.inventory.get(item, 0) < quantity:
        raise ValidationError(
            "A character cannot transfer more of an item than they hold."
        )
    return post_inventory_transaction(
        from_account=source.inventory_account(),
        to_account=recipient.inventory_account(),
        item=item,
        quantity=quantity,
        description=description,
    )


def take_loot(
    *, source: Character, item: CompendiumEntry, quantity: int, description: str = ""
) -> InventoryTransaction:
    """Remove held inventory by returning it to the campaign system account."""
    if quantity <= 0 or source.inventory.get(item, 0) < quantity:
        raise ValidationError(
            "A character cannot give up more of an item than they hold."
        )
    return post_inventory_transaction(
        from_account=source.inventory_account(),
        to_account=source.campaign.inventory_system_account(),
        item=item,
        quantity=quantity,
        description=description,
    )


def grant_coins(
    *, recipient: Character, coins: CoinAmounts, description: str = ""
) -> MoneyTransaction:
    """Create currency in the campaign system account and grant it to a character."""
    amounts = _normalise_coins(coins)
    system = recipient.campaign.money_system_account()
    account = recipient.money_account()
    entries = [
        (system, denomination, -amount) for denomination, amount in amounts.items()
    ]
    entries.extend(
        (account, denomination, amount) for denomination, amount in amounts.items()
    )
    return post_money_transaction(entries, description=description)


def spend_coins(
    *, spender: Character, coins: CoinAmounts, description: str = ""
) -> MoneyTransaction:
    """Remove currency from a character by returning it to the campaign system account."""
    amounts = _normalise_coins(coins)
    _ensure_character_has_coins(spender, amounts)
    account = spender.money_account()
    system = spender.campaign.money_system_account()
    entries = [
        (account, denomination, -amount) for denomination, amount in amounts.items()
    ]
    entries.extend(
        (system, denomination, amount) for denomination, amount in amounts.items()
    )
    return post_money_transaction(entries, description=description)


def exchange_coins(
    *,
    character: Character,
    given: CoinAmounts,
    received: CoinAmounts,
    description: str = "",
) -> MoneyTransaction:
    """Exchange a character's coins without changing their total copper value."""
    given_amounts = _normalise_coins(given)
    received_amounts = _normalise_coins(received)
    _ensure_character_has_coins(character, given_amounts)
    given_value = sum(
        COPPER_VALUES[denomination] * amount
        for denomination, amount in given_amounts.items()
    )
    received_value = sum(
        COPPER_VALUES[denomination] * amount
        for denomination, amount in received_amounts.items()
    )
    if given_value != received_value:
        raise ValidationError("Coin exchanges must have equal copper value.")
    account = character.money_account()
    entries = [
        (account, denomination, -amount)
        for denomination, amount in given_amounts.items()
    ]
    entries.extend(
        (account, denomination, amount)
        for denomination, amount in received_amounts.items()
    )
    return post_money_transaction(entries, description=description)


def preview_shared_experience(*, character: Character, amount: int) -> int:
    """Return XP per eligible character without posting an award."""
    return character.campaign.award_shared_experience(amount, dry_run=True)


def reverse_transaction(
    transaction_to_reverse: LedgerTransaction, *, description: str = ""
) -> LedgerTransaction:
    """Reverse one posted ledger transaction, selecting its concrete ledger service."""
    if isinstance(transaction_to_reverse, InventoryTransaction):
        return reverse_inventory_transaction(
            transaction_to_reverse, description=description
        )
    if isinstance(transaction_to_reverse, MoneyTransaction):
        return reverse_money_transaction(
            transaction_to_reverse, description=description
        )
    return reverse_experience_transaction(
        transaction_to_reverse, description=description
    )
