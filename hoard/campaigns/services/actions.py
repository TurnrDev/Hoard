from __future__ import annotations

from collections.abc import Mapping

from django.core.exceptions import ValidationError

from ..models import Character, ExperienceTransaction, MoneyEntry, MoneyTransaction
from .experience import reverse_experience_transaction
from .ledger import COPPER_VALUES, post_money_transaction, reverse_money_transaction

type CoinAmounts = Mapping[str | MoneyEntry.Denomination, int]
type LedgerTransaction = MoneyTransaction | ExperienceTransaction


def normalize_coins(
    coins: CoinAmounts,
) -> dict[MoneyEntry.Denomination, int]:
    amounts: dict[MoneyEntry.Denomination, int] = {}
    for denomination, amount in coins.items():
        try:
            normalized = MoneyEntry.Denomination(denomination)
        except ValueError as error:
            raise ValidationError(
                f"Unknown currency denomination: {denomination}."
            ) from error
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValidationError("Coin amounts must be positive integers.")
        amounts[normalized] = amounts.get(normalized, 0) + amount
    if not amounts:
        raise ValidationError("At least one coin amount is required.")
    return amounts


def ensure_character_has_coins(
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


def grant_coins(
    *, recipient: Character, coins: CoinAmounts, description: str = ""
) -> MoneyTransaction:
    """Create currency in the campaign system account and grant it to a character."""
    amounts = normalize_coins(coins)
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
    amounts = normalize_coins(coins)
    ensure_character_has_coins(spender, amounts)
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
    given_amounts = normalize_coins(given)
    received_amounts = normalize_coins(received)
    ensure_character_has_coins(character, given_amounts)
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
    """Reverse one posted money or experience ledger transaction."""
    if isinstance(transaction_to_reverse, MoneyTransaction):
        return reverse_money_transaction(
            transaction_to_reverse, description=description
        )
    return reverse_experience_transaction(
        transaction_to_reverse, description=description
    )
