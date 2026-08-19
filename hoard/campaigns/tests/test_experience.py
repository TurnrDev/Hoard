from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, ExperienceTransaction
from hoard.campaigns.services import reverse_experience_transaction

from .helpers import make_character


class SharedExperienceTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")

    def test_dry_run_returns_share_without_side_effects(self) -> None:
        recipients = [
            make_character(self.campaign, f"Hero {index}") for index in range(5)
        ]
        for character in recipients:
            character.activate()
        self.assertEqual(self.campaign.award_shared_experience(11, dry_run=True), 2)
        self.assertEqual(ExperienceTransaction.objects.count(), 0)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.shared_experience, 0)

        self.assertEqual(self.campaign.award_shared_experience(11), 2)
        self.assertEqual([character.experience for character in recipients], [2] * 5)
        award = ExperienceTransaction.objects.get()
        self.assertEqual(award.discarded_amount, 1)

    def test_active_player_characters_only_receive_xp_and_late_joiners_catch_up(
        self,
    ) -> None:
        active = make_character(self.campaign, "Active")
        active.activate()
        inactive = make_character(self.campaign, "Inactive")
        npc = make_character(self.campaign, "NPC", active=True, player=False)
        self.campaign.award_shared_experience(10)
        self.assertEqual(active.experience, 10)
        self.assertEqual(inactive.experience, 0)
        self.assertEqual(npc.experience, 0)

        inactive.activate()
        self.assertEqual(inactive.experience, 10)

    def test_invalid_awards_and_reversal_are_handled(self) -> None:
        with self.assertRaises(ValidationError):
            self.campaign.award_shared_experience(1)
        character = make_character(self.campaign)
        character.activate()
        with self.assertRaises(ValidationError):
            self.campaign.award_shared_experience(0)
        self.campaign.use_shared_exp = False
        self.campaign.save()
        with self.assertRaises(ValidationError):
            self.campaign.award_shared_experience(10)

        self.campaign.use_shared_exp = True
        self.campaign.save()
        self.campaign.award_shared_experience(10)
        award = ExperienceTransaction.objects.get()
        reverse_experience_transaction(award)
        self.campaign.refresh_from_db()
        self.assertEqual(character.experience, 0)
        self.assertEqual(self.campaign.shared_experience, 0)
