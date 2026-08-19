# Ledger guide

This guide describes the campaign ledger for API and UI design. It also gives a
plain-language explanation of what the system records.

## Concepts

A **transaction** is one complete event: loot, a purchase, a transfer, an XP
award, or a correction. A transaction contains signed **entries**. An
**account** belongs either to a character or to the campaign system. The system
account is the other side of loot, merchant, and DM-award events.

Every posted transaction balances:

- Inventory quantities balance to zero for each item.
- Money balances to zero after converting coins to copper value.
- XP balances to zero.

Character inventory, money, and XP are calculated from entries. A posted entry
is immutable. Correct mistakes by creating a linked reversal, then post a
replacement transaction if needed.

## Public developer API

Import models from `hoard.campaigns.models` and services from
`hoard.campaigns.services`. Those paths are stable even though the
implementation is separated into focused modules.

```python
from hoard.campaigns.models import MoneyEntry
from hoard.campaigns.services import (
    post_inventory_transaction,
    post_money_transaction,
)

inventory_system = campaign.inventory_system_account()
character_inventory = character.inventory_account()
post_inventory_transaction(
    from_account=inventory_system,
    to_account=character_inventory,
    item=torch,
    quantity=2,
    description="Found two torches",
)

money_system = campaign.money_system_account()
character_money = character.money_account()
post_money_transaction(
    [
        (money_system, MoneyEntry.Denomination.GOLD, -5),
        (character_money, MoneyEntry.Denomination.GOLD, 5),
    ],
    description="Quest reward",
)
```

Use `reverse_inventory_transaction`, `reverse_money_transaction`, or
`reverse_experience_transaction` for corrections. Do not update or delete
entries directly.

## Shared XP API

```python
per_character = campaign.award_shared_experience(11, dry_run=True)
assert per_character == 2

per_character = campaign.award_shared_experience(11, description="Rat fight")
assert per_character == 2
```

Dry runs validate the award and return the XP that each eligible character
would receive. They do not create entries or update the campaign. A real award
returns the same per-character amount, records a balanced XP transaction, and
updates the shared-XP baseline.

Eligible recipients are active characters linked to a PC campaign context. NPCs and
inactive characters are excluded. The award is divided by recipient count,
rounded down, and the remainder is discarded. A newly activated player
character receives a baseline transaction that aligns it with the group.

## UI design requirements

- Present a transaction as one human-readable event with its entries grouped
  beneath it; normal users should not need to enter signed values manually.
- Provide dedicated forms for loot, transfers, purchases, coin exchanges, and
  shared XP; have the server construct the balanced entries. Inventory transfer
  forms provide a source, destination, item, and positive quantity.
- Show current character balances alongside their transaction history.
- Preview shared XP with `dry_run=True` before the confirmation action.
- Disable editing and deleting posted transactions. Offer a **Reverse** action
  that asks for a correction description and links the resulting transaction to
  the original.
- Surface validation failures before posting: no recipients, zero XP share,
  cross-campaign accounts, non-zero inventory imbalance, and non-zero
  copper-equivalent money imbalance.
