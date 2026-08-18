from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, InventoryItem, MoneyEntry
from hoard.campaigns.services import (
    post_inventory_transaction,
    post_money_transaction,
    reverse_inventory_transaction,
)

from .helpers import make_character


class LedgerTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name='Hoard')
        self.character = make_character(self.campaign)

    def test_inventory_entries_balance_are_immutable_and_reversible(self) -> None:
        item = InventoryItem.objects.create(campaign=self.campaign, name='Torch')
        system = self.campaign.inventory_system_account()
        account = self.character.inventory_account()
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

    def test_money_tracks_coins_and_decimal_gold_value(self) -> None:
        system = self.campaign.money_system_account()
        account = self.character.money_account()
        post_money_transaction([
            (system, MoneyEntry.Denomination.GOLD, -1),
            (account, MoneyEntry.Denomination.GOLD, 1),
        ])
        post_money_transaction([
            (account, MoneyEntry.Denomination.GOLD, -1),
            (account, MoneyEntry.Denomination.SILVER, 10),
        ])
        self.assertEqual(self.character.money.gold, 0)
        self.assertEqual(self.character.money.silver, 10)
        self.assertEqual(self.character.money.gold_value, Decimal('1.0'))
        with self.assertRaises(ValidationError):
            post_money_transaction([(account, MoneyEntry.Denomination.GOLD, 1)])

    def test_cross_campaign_inventory_and_money_operations_are_rejected(self) -> None:
        other_campaign = Campaign.objects.create(name='Other')
        other_character = make_character(other_campaign, 'Other hero')
        item = InventoryItem.objects.create(campaign=self.campaign, name='Torch')

        with self.assertRaises(ValidationError):
            post_inventory_transaction(
                from_account=self.campaign.inventory_system_account(),
                to_account=other_character.inventory_account(),
                item=item,
                quantity=1,
            )
        with self.assertRaises(ValidationError):
            post_money_transaction([
                (self.character.money_account(), MoneyEntry.Denomination.GOLD, -1),
                (other_character.money_account(), MoneyEntry.Denomination.GOLD, 1),
            ])
