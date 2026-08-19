from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from hoard.campaigns.models import Campaign, Character, Player

from .helpers import make_character


class CoreModelTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")

    def test_player_membership_is_unique_per_campaign(self) -> None:
        user = get_user_model().objects.create_user(username="jay")
        Player.objects.create(campaign=self.campaign, user=user)
        with self.assertRaises(IntegrityError):
            Player.objects.create(campaign=self.campaign, user=user)

    def test_only_one_active_character_is_allowed_per_player(self) -> None:
        character = make_character(self.campaign)
        character.activate()
        with self.assertRaises(IntegrityError):
            Character.objects.create(
                campaign=self.campaign,
                player=character.player,
                name="Backup",
                race="Elf",
                character_class="Wizard",
                strength=8,
                dexterity=14,
                constitution=10,
                intelligence=16,
                wisdom=12,
                charisma=10,
                is_active=True,
            )
