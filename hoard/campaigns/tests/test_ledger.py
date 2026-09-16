from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, MoneyEntry
from hoard.campaigns.services import (
    grant_coins,
    post_money_transaction,
    reverse_money_transaction,
)

from .helpers import make_character


class LedgerTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        self.character = make_character(self.campaign)

    def test_money_tracks_coins_and_decimal_gold_value(self) -> None:
        system = self.campaign.money_system_account()
        account = self.character.money_account()
        post_money_transaction(
            [
                (system, MoneyEntry.Denomination.GOLD, -1),
                (account, MoneyEntry.Denomination.GOLD, 1),
            ]
        )
        post_money_transaction(
            [
                (account, MoneyEntry.Denomination.GOLD, -1),
                (account, MoneyEntry.Denomination.SILVER, 10),
            ]
        )
        self.assertEqual(self.character.money.gold, 0)
        self.assertEqual(self.character.money.silver, 10)
        self.assertEqual(self.character.money.gold_value, Decimal("1.0"))
        with self.assertRaises(ValidationError):
            post_money_transaction([(account, MoneyEntry.Denomination.GOLD, 1)])

    def test_every_denomination_contributes_to_decimal_gold_value(self) -> None:
        grant_coins(
            recipient=self.character,
            coins={"cp": 1, "sp": 1, "ep": 1, "gp": 1, "pp": 1},
        )

        balance = self.character.money

        self.assertEqual(
            (
                balance.copper,
                balance.silver,
                balance.electrum,
                balance.gold,
                balance.platinum,
            ),
            (1, 1, 1, 1, 1),
        )
        self.assertEqual(balance.gold_value, Decimal("11.61"))

    def test_system_accounts_are_created_once_and_transactions_balance(self) -> None:
        first_money_system = self.campaign.money_system_account()
        second_money_system = self.campaign.money_system_account()
        first_experience_system = self.campaign.experience_system_account()
        second_experience_system = self.campaign.experience_system_account()

        self.assertEqual(first_money_system.pk, second_money_system.pk)
        self.assertEqual(first_experience_system.pk, second_experience_system.pk)

        posted = grant_coins(recipient=self.character, coins={"gp": 3, "sp": 4})
        copper_values = {
            MoneyEntry.Denomination.COPPER: 1,
            MoneyEntry.Denomination.SILVER: 10,
            MoneyEntry.Denomination.ELECTRUM: 50,
            MoneyEntry.Denomination.GOLD: 100,
            MoneyEntry.Denomination.PLATINUM: 1000,
        }
        copper_value = sum(
            entry.amount * copper_values[entry.denomination]
            for entry in posted.entries.all()
        )

        self.assertEqual(copper_value, 0)

    def test_money_reversal_restores_balances_and_is_single_use(self) -> None:
        posted = grant_coins(recipient=self.character, coins={"gp": 3, "sp": 4})

        reversal = reverse_money_transaction(posted)

        self.assertEqual(self.character.money.gold_value, Decimal("0"))
        self.assertEqual(
            sorted(entry.amount for entry in reversal.entries.all()),
            [-4, -3, 3, 4],
        )
        with self.assertRaises(ValidationError):
            reverse_money_transaction(posted)

    def test_cross_campaign_money_operations_are_rejected(self) -> None:
        other_campaign = Campaign.objects.create(name="Other")
        other_character = make_character(other_campaign, "Other hero")
        with self.assertRaises(ValidationError):
            post_money_transaction(
                [
                    (self.character.money_account(), MoneyEntry.Denomination.GOLD, -1),
                    (other_character.money_account(), MoneyEntry.Denomination.GOLD, 1),
                ]
            )
