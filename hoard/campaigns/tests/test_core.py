from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext, Character


class CoreModelTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        self.user = get_user_model().objects.create_user(username="jay")

    def test_a_user_can_hold_gm_and_pc_contexts(self) -> None:
        CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )
        pc = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.PC
        )
        Character.objects.create(
            campaign=self.campaign,
            context=pc,
            kind=Character.Kind.PC,
            name="Hero",
            race="Human",
            character_class="Fighter",
        )

        with self.assertRaises(IntegrityError):
            CampaignContext.objects.create(
                campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
            )

    def test_campaign_context_role_is_immutable(self) -> None:
        context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )
        context.kind = CampaignContext.Kind.PC

        with self.assertRaises(ValidationError):
            context.save()

    def test_character_requires_a_player_context(self) -> None:
        gm_context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )

        with self.assertRaises(ValidationError):
            Character.objects.create(
                campaign=self.campaign,
                context=gm_context,
                kind=Character.Kind.PC,
                name="GM character",
            )

    def test_npc_cannot_have_a_player_context(self) -> None:
        pc_context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.PC
        )

        with self.assertRaises(ValidationError):
            Character.objects.create(
                campaign=self.campaign,
                context=pc_context,
                kind=Character.Kind.NPC,
                name="Owned NPC",
            )

    def test_campaign_calendar_rolls_between_years(self) -> None:
        self.campaign.calendar_year = 81
        self.campaign.calendar_day = 365
        self.campaign.adjust_calendar_day(1)
        self.assertEqual(
            (self.campaign.calendar_year, self.campaign.calendar_day), (82, 1)
        )
        self.campaign.adjust_calendar_day(-1)
        self.assertEqual(
            (self.campaign.calendar_year, self.campaign.calendar_day), (81, 365)
        )

    def test_campaign_calendar_cannot_precede_first_day(self) -> None:
        self.campaign.calendar_year = 1
        self.campaign.calendar_day = 1

        with self.assertRaises(ValidationError):
            self.campaign.adjust_calendar_day(-1)

    def test_level_thresholds_are_retained(self) -> None:
        self.assertEqual(Character.level_for_experience(6500), 5)
        self.assertEqual(Character.level_for_experience(6499), 4)
