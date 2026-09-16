from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, MoneyEntry
from hoard.campaigns.services import (
    exchange_coins,
    grant_coins,
    spend_coins,
)

from .helpers import make_character


class CampaignActionTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        self.first = make_character(self.campaign, "First")

    def test_grant_spend_and_exchange_coins(self) -> None:
        grant_coins(recipient=self.first, coins={"gp": 2})
        exchange_coins(character=self.first, given={"gp": 1}, received={"sp": 10})
        spend_coins(spender=self.first, coins={"gp": 1, "sp": 10})
        self.assertEqual(self.first.money.gold_value, 0)
        with self.assertRaises(ValidationError):
            spend_coins(spender=self.first, coins={MoneyEntry.Denomination.GOLD: 1})
        with self.assertRaises(ValidationError):
            exchange_coins(character=self.first, given={"cp": 1}, received={"sp": 1})
