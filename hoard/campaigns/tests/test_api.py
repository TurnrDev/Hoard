from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings

from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    ExperienceTransaction,
    MembershipEvent,
    MoneyTransaction,
)

from .helpers import ContextSocketMixin


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
)
class ContextApiTests(ContextSocketMixin, TransactionTestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        user_model = get_user_model()
        self.gm_user = user_model.objects.create_user(username="gm")
        self.player_user = user_model.objects.create_user(username="player")
        self.other_user = user_model.objects.create_user(username="other")
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.gm_user,
            kind=CampaignContext.Kind.GM,
        )
        self.pc = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.player_user,
            kind=CampaignContext.Kind.PC,
        )
        self.other_pc = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.other_user,
            kind=CampaignContext.Kind.PC,
        )
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.pc,
            kind=Character.Kind.PC,
            is_active=True,
            name="Hero",
            race="Human",
            character_class="Fighter",
        )
        self.other_character = Character.objects.create(
            campaign=self.campaign,
            context=self.other_pc,
            kind=Character.Kind.PC,
            is_active=True,
            name="Other hero",
        )

    def test_players_can_view_calendar_but_only_gms_can_adjust_it(self) -> None:
        visible = self.socket_request(
            self.player_user, self.pc.pk, "campaign.calendar.get"
        )
        self.assertEqual(visible["data"]["year"], 81)

        forbidden = self.socket_request(
            self.player_user, self.pc.pk, "campaign.calendar.adjust", amount=1
        )
        self.assertEqual(forbidden["type"], "command.error")

        updated = self.socket_request(
            self.gm_user, self.gm.pk, "campaign.calendar.adjust", amount=1
        )
        self.assertEqual(updated["type"], "command.ack")
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.calendar_day, 138)

    def test_profile_query_and_owner_update_use_minimal_fields(self) -> None:
        result = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.get",
            character_id=self.character.pk,
        )
        self.assertEqual(
            {
                "name": result["data"]["name"],
                "race": result["data"]["race"],
                "class": result["data"]["class"],
                "kind": result["data"]["kind"],
            },
            {
                "name": "Hero",
                "race": "Human",
                "class": "Fighter",
                "kind": "pc",
            },
        )
        self.assertNotIn("sheet", result["data"])
        self.assertNotIn("inventory", result["data"])
        self.assertNotIn("conditions", result["data"])

        updated = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.update",
            character_id=self.character.pk,
            fields={"name": "Renamed", "race": "Elf", "character_class": "Wizard"},
        )
        self.assertEqual(updated["type"], "command.ack")
        self.character.refresh_from_db()
        self.assertEqual(
            (self.character.name, self.character.race, self.character.character_class),
            ("Renamed", "Elf", "Wizard"),
        )

    def test_player_cannot_edit_another_character(self) -> None:
        response = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.update",
            character_id=self.other_character.pk,
            fields={"name": "Not allowed"},
        )

        self.assertEqual(response["type"], "command.error")
        self.other_character.refresh_from_db()
        self.assertEqual(self.other_character.name, "Other hero")

    def test_only_game_master_can_create_an_npc(self) -> None:
        denied = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.create",
            fields={
                "name": "Guide",
                "race": "Human",
                "character_class": "Expert",
                "is_npc": True,
            },
        )
        self.assertEqual(denied["type"], "command.error")

        created = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "characters.create",
            fields={
                "name": "Guide",
                "race": "Human",
                "character_class": "Expert",
                "is_npc": True,
            },
        )
        self.assertEqual(created["type"], "command.ack")
        npc = Character.objects.get(name="Guide")
        self.assertEqual(npc.kind, Character.Kind.NPC)
        self.assertTrue(npc.is_active)
        self.assertIsNone(npc.context_id)

    def test_only_game_master_can_deactivate_members_and_change_is_audited(
        self,
    ) -> None:
        denied = self.socket_request(
            self.player_user,
            self.pc.pk,
            "campaign.members.deactivate",
            member_id=self.other_pc.pk,
        )
        self.assertEqual(denied["type"], "command.error")

        accepted = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "campaign.members.deactivate",
            member_id=self.other_pc.pk,
        )
        self.assertEqual(accepted["type"], "command.ack")

        self.other_pc.refresh_from_db()
        self.other_character.refresh_from_db()
        self.assertFalse(self.other_pc.is_active)
        self.assertFalse(self.other_character.is_active)

        event = MembershipEvent.objects.get(subject=self.other_pc)
        self.assertEqual(event.created_by, self.gm)
        self.assertEqual(event.reason, MembershipEvent.Reason.DEACTIVATED)
        self.assertEqual(event.before["is_active"], True)
        self.assertEqual(event.after["is_active"], False)

    def test_money_and_experience_commands_enforce_campaign_roles(self) -> None:
        denied_award = self.socket_request(
            self.player_user,
            self.pc.pk,
            "experience.shared_awards.create",
            amount=100,
            description="Not permitted",
        )
        self.assertEqual(denied_award["type"], "command.error")
        self.assertFalse(ExperienceTransaction.objects.exists())

        accepted_award = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "experience.shared_awards.create",
            amount=101,
            description="Quest reward",
        )
        self.assertEqual(accepted_award["type"], "command.ack")
        self.assertEqual(ExperienceTransaction.objects.count(), 1)

        grant = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "money.transfers.create",
            from_character_id=None,
            to_character_id=self.character.pk,
            amounts={"gp": 2},
            description="Starting funds",
        )
        self.assertEqual(grant["type"], "command.ack")

        forbidden_transfer = self.socket_request(
            self.player_user,
            self.pc.pk,
            "money.transfers.create",
            from_character_id=self.other_character.pk,
            to_character_id=self.character.pk,
            amounts={"gp": 1},
            description="Not mine",
        )
        self.assertEqual(forbidden_transfer["type"], "command.error")

        own_transfer = self.socket_request(
            self.player_user,
            self.pc.pk,
            "money.transfers.create",
            from_character_id=self.character.pk,
            to_character_id=self.other_character.pk,
            amounts={"gp": 1},
            description="Shared funds",
        )
        self.assertEqual(own_transfer["type"], "command.ack")
        latest = MoneyTransaction.objects.order_by("-occurred_at", "-pk").first()
        self.assertEqual(latest.created_by, self.pc)

        reversed_transaction = self.socket_request(
            self.player_user,
            self.pc.pk,
            "transactions.reverse",
            ledger="money",
            transaction_id=latest.pk,
        )
        self.assertEqual(reversed_transaction["type"], "command.ack")
        self.assertEqual(latest.reversal.created_by, self.pc)

    def test_portrait_upload_requires_character_permission(self) -> None:
        image = SimpleUploadedFile(
            "portrait.png",
            b"\x89PNG\r\n\x1a\n" + b"image-data",
            content_type="image/png",
        )
        self.client.force_login(self.other_user)
        denied = self.client.post(
            f"/api/uploads/character-portraits/{self.other_pc.pk}/{self.character.pk}/",
            {"file": image},
        )
        self.assertEqual(denied.status_code, 403)

        image = SimpleUploadedFile(
            "portrait.png",
            b"\x89PNG\r\n\x1a\n" + b"image-data",
            content_type="image/png",
        )
        self.client.force_login(self.player_user)
        accepted = self.client.post(
            f"/api/uploads/character-portraits/{self.pc.pk}/{self.character.pk}/",
            {"file": image},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(accepted.json()["portrait_url"])
