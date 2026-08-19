from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, InventoryItem, MoneyEntry
from hoard.campaigns.services import (
    exchange_coins,
    grant_coins,
    grant_loot,
    spend_coins,
    take_loot,
    transfer_item,
)

from .helpers import make_character


class CampaignActionTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        self.first = make_character(self.campaign, "First")
        self.second = make_character(self.campaign, "Second")
        self.item = InventoryItem.objects.create(
            campaign=None,
            name="Torch",
            source_identifier="torch",
            source_system="5e",
            source_repository="https://example.test",
        )

    def test_loot_and_item_transfer_require_available_inventory(self) -> None:
        grant_loot(recipient=self.first, item=self.item, quantity=2)
        transfer_item(
            source=self.first, recipient=self.second, item=self.item, quantity=1
        )
        self.assertEqual(self.first.inventory[self.item], 1)
        self.assertEqual(self.second.inventory[self.item], 1)
        take_loot(source=self.second, item=self.item, quantity=1)
        self.assertNotIn(self.item, self.second.inventory)
        with self.assertRaises(ValidationError):
            transfer_item(
                source=self.first, recipient=self.second, item=self.item, quantity=2
            )

    def test_grant_spend_and_exchange_coins(self) -> None:
        grant_coins(recipient=self.first, coins={"gp": 2})
        exchange_coins(character=self.first, given={"gp": 1}, received={"sp": 10})
        spend_coins(spender=self.first, coins={"gp": 1, "sp": 10})
        self.assertEqual(self.first.money.gold_value, 0)
        with self.assertRaises(ValidationError):
            spend_coins(spender=self.first, coins={MoneyEntry.Denomination.GOLD: 1})
        with self.assertRaises(ValidationError):
            exchange_coins(character=self.first, given={"cp": 1}, received={"sp": 1})
