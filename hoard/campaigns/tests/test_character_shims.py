from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    PartyExperienceAward,
)


class CharacterShimTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="DiceCloud campaign")
        self.user = get_user_model().objects.create_user(
            username="player", password="test-password"
        )
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.PC,
        )

    def test_unlinked_character_cannot_be_active(self) -> None:
        with self.assertRaises(ValidationError):
            Character.objects.create(
                campaign=self.campaign,
                context=self.context,
                is_active=True,
            )

    def test_unowned_player_shim_does_not_require_a_user(self) -> None:
        character = Character.objects.create(campaign=self.campaign)

        self.assertIsNone(character.context_id)
        self.assertEqual(str(character), f"Unlinked player {character.pk}")

    def test_local_name_and_hp_are_used_only_without_dicecloud(self) -> None:
        from hoard.campaigns.api import character_data

        character = Character.objects.create(
            campaign=self.campaign,
            name="Ama",
            current_hp=32,
            max_hp=46,
            is_active=True,
        )

        fallback_data = character_data(character, projection=None)
        self.assertEqual(fallback_data["name"], "Ama")
        self.assertEqual(fallback_data["current_hp"], 32)
        self.assertEqual(fallback_data["max_hp"], 46)

        character.dicecloud_creature_id = "sfdxGdwav3hoNATLJ"
        character.save(update_fields=("dicecloud_creature_id",))
        dicecloud_data = character_data(character, projection={"name": "DiceCloud Ama"})
        self.assertEqual(dicecloud_data["name"], "DiceCloud Ama")
        self.assertIsNone(dicecloud_data["current_hp"])
        self.assertIsNone(dicecloud_data["max_hp"])

        unavailable_data = character_data(character, projection={"unavailable": True})
        self.assertEqual(unavailable_data["name"], f"Linked player {character.pk}")

    def test_party_xp_uses_campaign_recipient_count_without_sheets(self) -> None:
        self.campaign.experience_recipient_count = 2
        self.campaign.save(update_fields=("experience_recipient_count",))

        award = self.campaign.award_shared_experience(
            7, description="Encounter award", return_transaction=True
        )

        self.campaign.refresh_from_db()
        posted = PartyExperienceAward.objects.get()
        self.assertEqual(award[0], 3)
        self.assertEqual(self.campaign.shared_experience, 3)
        self.assertEqual(posted.recipient_count, 2)
        self.assertEqual(posted.discarded_amount, 1)
