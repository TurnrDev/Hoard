from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterLevelProgress,
    HealthTransaction,
    format_campaign_date,
    ordinal,
)
from hoard.campaigns.services import (
    accept_invitation,
    approve_campaign_level,
    create_invitation,
    post_health_transaction,
)


class DateAndHealthTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(
            name="Dated campaign",
            calendar_era_abbreviation="PD",
            calendar_year=81,
            calendar_day=11,
            level=3,
        )
        self.user = get_user_model().objects.create_user(username="player")
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.PC,
        )
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.context,
            is_active=True,
            name="Hero",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            base_hp=20,
            hp_adjustment=2,
            current_hp=10,
            temporary_hp=3,
        )

    def test_shared_ordinal_rule_and_required_format(self) -> None:
        self.assertEqual(
            [ordinal(day) for day in (1, 2, 3, 4, 11, 12, 13, 21)],
            ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st"],
        )
        self.assertEqual(format_campaign_date("PD", 81, 21), "PD 81, 21st")

    def test_hp_uses_base_ability_per_level_and_hp_only_adjustment(self) -> None:
        self.assertEqual(self.character.max_hp, 28)

    def test_health_transaction_snapshots_both_dates_and_balances(self) -> None:
        posted = post_health_transaction(
            self.character,
            reason=HealthTransaction.Reason.DAMAGE,
            current_hp_delta=-4,
            description="Trap",
            created_by=self.context,
        )
        self.campaign.calendar_day = 12
        self.campaign.save(update_fields=("calendar_day",))

        self.character.refresh_from_db()
        self.assertEqual(
            (self.character.current_hp, self.character.temporary_hp), (9, 0)
        )
        self.assertEqual((posted.current_hp_delta, posted.temporary_hp_delta), (-1, -3))
        self.assertEqual(posted.campaign_date, "PD 81, 11th")
        self.assertIsNotNone(posted.occurred_at.tzinfo)
        with self.assertRaises(ValidationError):
            posted.delete()


class InvitationAndLevelTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(
            name="Progression", shared_experience=300
        )
        self.gm_user = get_user_model().objects.create_user(username="gm")
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.gm_user,
            kind=CampaignContext.Kind.GM,
        )

    def test_accepting_invite_creates_inactive_draft_and_is_single_use(self) -> None:
        invitation, token = create_invitation(self.gm, "delivery@example.com")
        player = get_user_model().objects.create_user(username="invited")

        context = accept_invitation(token, player)

        character = context.character
        self.assertFalse(character.is_active)
        self.assertFalse(character.is_build_complete)
        self.assertTrue(character.health_history.filter(reason="baseline").exists())
        invitation.refresh_from_db()
        self.assertEqual(invitation.accepted_by, player)
        with self.assertRaises(ValidationError):
            accept_invitation(
                token, get_user_model().objects.create_user(username="late")
            )

    def test_gm_approval_is_immediate_and_blocks_until_active_players_finish(
        self,
    ) -> None:
        player = get_user_model().objects.create_user(username="active")
        context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=player,
            kind=CampaignContext.Kind.PC,
        )
        character = Character.objects.create(
            campaign=self.campaign,
            context=context,
            is_active=True,
            name="Active",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )

        event = approve_campaign_level(self.campaign, created_by=self.gm)

        self.campaign.refresh_from_db()
        self.assertEqual((event.previous_level, event.next_level), (1, 2))
        self.assertEqual(self.campaign.level, 2)
        self.assertFalse(
            CharacterLevelProgress.objects.get(character=character, level=2).is_complete
        )
        self.campaign.shared_experience = 900
        self.campaign.save(update_fields=("shared_experience",))
        with self.assertRaises(ValidationError):
            approve_campaign_level(self.campaign, created_by=self.gm)


class ConcurrentInvitationTests(TransactionTestCase):
    reset_sequences = True

    def test_only_one_concurrent_claim_can_accept_a_token(self) -> None:
        campaign = Campaign.objects.create(name="Concurrent invites")
        gm_user = get_user_model().objects.create_user(username="concurrent-gm")
        gm = CampaignContext.objects.create(
            campaign=campaign, user=gm_user, kind=CampaignContext.Kind.GM
        )
        _, token = create_invitation(gm)
        users = [
            get_user_model().objects.create_user(username=f"claimant-{index}")
            for index in range(2)
        ]

        def claim(user_id: int) -> bool:
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                accept_invitation(token, user)
            except ValidationError:
                return False
            finally:
                close_old_connections()
            return True

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(claim, [user.pk for user in users]))

        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(
            CampaignContext.objects.filter(
                campaign=campaign, kind=CampaignContext.Kind.PC
            ).count(),
            1,
        )
