from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, InventoryAccount, InventoryItem, MoneyAccount, MoneyEntry
from hoard.campaigns.services import (
    character_account,
    post_inventory_transaction,
    post_money_transaction,
    reverse_inventory_transaction,
    system_account,
)

from .helpers import make_character


class LedgerTests(TestCase):
    def setUp(self):
        self.campaign = Campaign.objects.create(name='Hoard')
        self.character = make_character(self.campaign)

    def test_inventory_entries_balance_are_immutable_and_reversible(self):
        item = InventoryItem.objects.create(campaign=self.campaign, name='Torch')
        system = system_account(InventoryAccount, self.campaign)
        account = character_account(InventoryAccount, self.character)
        posted = post_inventory_transaction(
            from_account=system,
            to_account=account,
            item=item,
            quantity=2,
        )

        self.assertEqual(self.character.inventory, {item: 2})
        entry = posted.entries.filter(account=account).get()
        entry.amount = 3
        with self.assertRaises(ValidationError):
            entry.save()
        reverse_inventory_transaction(posted)
        self.assertEqual(self.character.inventory, {})
        with self.assertRaises(ValidationError):
            post_inventory_transaction(
                from_account=account,
                to_account=account,
                item=item,
                quantity=1,
            )

    def test_money_tracks_coins_and_decimal_gold_value(self):
        system = system_account(MoneyAccount, self.campaign)
        account = character_account(MoneyAccount, self.character)
        post_money_transaction(self.campaign, [
            (system, MoneyEntry.Denomination.GOLD, -1),
            (account, MoneyEntry.Denomination.GOLD, 1),
        ])
        post_money_transaction(self.campaign, [
            (account, MoneyEntry.Denomination.GOLD, -1),
            (account, MoneyEntry.Denomination.SILVER, 10),
        ])
        self.assertEqual(self.character.money.gold, 0)
        self.assertEqual(self.character.money.silver, 10)
        self.assertEqual(self.character.money.gold_value, Decimal('1.0'))
        with self.assertRaises(ValidationError):
            post_money_transaction(self.campaign, [(account, MoneyEntry.Denomination.GOLD, 1)])
