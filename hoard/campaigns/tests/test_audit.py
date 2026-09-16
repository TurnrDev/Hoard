from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext
from hoard.campaigns.services import grant_coins

from .helpers import make_character


class AuditEventTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(
            name="Audit",
            calendar_era_abbreviation="AE",
            calendar_year=42,
            calendar_day=12,
        )
        user = get_user_model().objects.create_user(username="auditor")
        self.actor = CampaignContext.objects.create(
            campaign=self.campaign,
            user=user,
            kind=CampaignContext.Kind.GM,
        )
        self.character = make_character(self.campaign)

    def test_transaction_snapshots_actor_timestamp_and_campaign_date(self) -> None:
        transaction = grant_coins(recipient=self.character, coins={"gp": 1})
        occurred_at = transaction.occurred_at
        transaction.created_by = self.actor
        transaction.save(update_fields=("created_by",))

        self.campaign.calendar_year = 43
        self.campaign.calendar_day = 1
        self.campaign.save(update_fields=("calendar_year", "calendar_day"))
        transaction.refresh_from_db()

        self.assertEqual(transaction.actor_username, "auditor")
        self.assertEqual(transaction.occurred_at, occurred_at)
        self.assertEqual(transaction.campaign_date, "AE 42, 12th")

    def test_transactions_and_entries_are_immutable(self) -> None:
        transaction = grant_coins(recipient=self.character, coins={"gp": 1})
        entry = transaction.entries.first()
        self.assertIsNotNone(entry)

        transaction.description = "Changed after posting"
        with self.assertRaises(ValidationError):
            transaction.save()
        with self.assertRaises(ValidationError):
            transaction.delete()

        entry.amount = 2
        with self.assertRaises(ValidationError):
            entry.save()
        with self.assertRaises(ValidationError):
            entry.delete()
