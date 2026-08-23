from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from hoard.campaigns.models import Campaign, CampaignContext
from hoard.campaigns.services import accept_invitation, create_invitation


class InvitationTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Invitations")
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
