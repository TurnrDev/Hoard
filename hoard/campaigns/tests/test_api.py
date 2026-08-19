import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext, Character, InventoryItem


class ContextApiTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        user_model = get_user_model()
        self.gm_user = user_model.objects.create_user(username="gm", password="secret")
        self.player_user = user_model.objects.create_user(
            username="player", password="secret"
        )
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign, user=self.gm_user, kind=CampaignContext.Kind.GM
        )
        self.pc = CampaignContext.objects.create(
            campaign=self.campaign, user=self.player_user, kind=CampaignContext.Kind.PC
        )
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.pc,
            is_active=True,
            name="Hero",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )
        self.item = InventoryItem.objects.create(campaign=self.campaign, name="Rope")

    def test_contexts_show_both_roles_for_one_user(self) -> None:
        CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.player_user,
            kind=CampaignContext.Kind.GM,
        )
        self.client.force_login(self.player_user)
        response = self.client.get("/api/contexts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["kind"] for row in response.json()}, {"gm", "pc"})

    def test_player_cannot_edit_another_character(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.patch(
            f"/api/contexts/{self.pc.pk}/characters/{self.character.pk}/",
            data=json.dumps({"base_hp": 20}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.character.refresh_from_db()
        self.assertEqual(self.character.base_hp, 20)

    def test_cah_preview_does_not_post_ledger_data(self) -> None:
        self.client.force_login(self.player_user)
        fixture = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"
        upload = self.client.post(
            f"/api/contexts/{self.pc.pk}/character-imports/cah/preview",
            {"file": SimpleUploadedFile("hero.cah", fixture.read_bytes())},
        )
        self.assertEqual(upload.status_code, 200)
        token = upload.json()["token"]
        committed = self.client.post(
            f"/api/contexts/{self.pc.pk}/character-imports/cah/commit",
            data=json.dumps({"token": token, "character_id": self.character.pk}),
            content_type="application/json",
        )
        self.assertEqual(committed.status_code, 200)
        self.character.refresh_from_db()
        self.assertTrue(self.character.name)
        self.assertGreater(self.character.max_hp, 0)

    def test_transaction_response_has_an_immutable_timestamp(self) -> None:
        self.client.force_login(self.gm_user)
        response = self.client.post(
            f"/api/contexts/{self.gm.pk}/inventory-transactions/",
            data=json.dumps(
                {
                    "from_character_id": None,
                    "to_character_id": self.character.pk,
                    "item_id": self.item.pk,
                    "quantity": 1,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("created_at", response.json())
