from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from hoard.campaigns.models import Campaign, InventoryItem, Player
from hoard.campaigns.services import grant_coins, grant_loot

from .helpers import make_character


class CampaignApiTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.gm_user = user_model.objects.create_user(
            username="gm", password="password"
        )
        self.player_user = user_model.objects.create_user(
            username="player", password="password"
        )
        self.campaign = Campaign.objects.create(name="Hoard")
        self.gm = Player.objects.create(
            campaign=self.campaign, user=self.gm_user, is_game_master=True
        )
        self.player = Player.objects.create(
            campaign=self.campaign, user=self.player_user
        )
        self.gm_character = make_character(self.campaign, "GM hero", player=self.gm)
        self.player_character = make_character(
            self.campaign, "Player hero", player=self.player
        )
        self.item = InventoryItem.objects.create(
            campaign=None,
            name="Torch",
            source_identifier="torch",
            source_system="5e",
            source_repository="https://example.test",
        )

    def test_members_can_create_items_and_transfer_loot_from_the_system(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/items/",
            {"name": "Homebrew rope", "description": "Very ropey."},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created_by_id"], self.player.pk)
        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": None,
                "to_character_id": self.player_character.pk,
                "item_id": self.item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        self.client.force_login(self.gm_user)
        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": None,
                "to_character_id": self.player_character.pk,
                "item_id": self.item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.player_character.inventory[self.item], 2)

    def test_players_only_receive_their_own_character_state(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.get(f"/api/campaigns/{self.campaign.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [character["id"] for character in response.json()["characters"]],
            [self.player_character.pk],
        )

    def test_members_can_create_items_with_equipment_metadata(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/items/",
            {
                "name": "Homebrew rapier",
                "description": "A fine blade.",
                "metadata": {
                    "category": "weapon",
                    "source_book": "Homebrew",
                    "item_type": "rapier",
                    "cost_amount": "25",
                    "cost_currency": "gp",
                    "weight_amount": "2",
                    "weight_unit": "pounds",
                    "rarity": "uncommon",
                    "is_magic": True,
                    "requires_attunement": False,
                },
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["equipment"]["category"], "weapon")
        self.assertEqual(response.json()["equipment"]["cost_currency"], "gp")

    def test_item_sources_filter_global_catalogue_but_do_not_strand_held_items(
        self,
    ) -> None:
        newer_item = InventoryItem.objects.create(
            campaign=None,
            name="2024 Torch",
            source_identifier="torch-2024",
            source_system="5e2024",
            source_repository="https://example.test",
        )
        self.client.force_login(self.gm_user)

        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": None,
                "to_character_id": self.player_character.pk,
                "item_id": newer_item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        self.campaign.item_sources = ["5e"]
        self.campaign.save()
        response = self.client.get(f"/api/campaigns/{self.campaign.pk}/items/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(newer_item.pk, [item["id"] for item in response.json()])

        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": None,
                "to_character_id": self.player_character.pk,
                "item_id": newer_item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": self.player_character.pk,
                "to_character_id": None,
                "item_id": newer_item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn(newer_item, self.player_character.inventory)

    def test_login_campaign_list_and_history_respect_membership(self) -> None:
        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get("/api/auth/csrf/")
        token = csrf_response.json()["csrfToken"]
        response = client.post(
            "/api/auth/session/",
            {"username": "player", "password": "password"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        response = client.get("/api/campaigns/")
        self.assertEqual(
            response.json(),
            [{"id": self.campaign.pk, "name": "Hoard", "is_game_master": False}],
        )

        grant_loot(recipient=self.gm_character, item=self.item, quantity=1)
        grant_loot(recipient=self.player_character, item=self.item, quantity=1)
        response = client.get(f"/api/campaigns/{self.campaign.pk}/transactions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        entries = response.json()["results"][0]["entries"]
        self.assertEqual(
            {entry["account_name"] for entry in entries},
            {"Campaign inventory system", "Player hero"},
        )

    def test_campaign_exposes_active_pc_balances_and_party_total(self) -> None:
        self.player_character.is_active = True
        self.player_character.save(update_fields=("is_active",))
        grant_coins(recipient=self.player_character, coins={"gp": 7})
        self.client.force_login(self.gm_user)

        response = self.client.get(f"/api/campaigns/{self.campaign.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["party_money"]["gp"], 7)
        character = next(
            item
            for item in response.json()["characters"]
            if item["id"] == self.player_character.pk
        )
        self.assertEqual(character["money"]["gp"], 7)

    def test_member_delete_revokes_access_and_archives_characters(self) -> None:
        self.client.force_login(self.gm_user)
        response = self.client.delete(
            f"/api/campaigns/{self.campaign.pk}/members/{self.player.pk}/"
        )

        self.assertEqual(response.status_code, 204)
        self.player.refresh_from_db()
        self.player_character.refresh_from_db()
        self.assertFalse(self.player.is_active)
        self.assertTrue(self.player_character.is_archived)

    def test_delete_latest_transaction_returns_reversal_and_gones_original(
        self,
    ) -> None:
        self.client.force_login(self.gm_user)
        created = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": None,
                "to_character_id": self.player_character.pk,
                "item_id": self.item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)

        deleted = self.client.delete(
            f"/api/campaigns/{self.campaign.pk}/transactions/inventory/{created.json()['id']}/"
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["reversal_of_id"], created.json()["id"])
        self.assertEqual(
            self.client.get(
                f"/api/campaigns/{self.campaign.pk}/transactions/inventory/{created.json()['id']}/"
            ).status_code,
            410,
        )

    def test_transaction_resources_reject_unheld_inventory_and_money(self) -> None:
        self.client.force_login(self.gm_user)
        inventory = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/inventory-transactions/",
            {
                "from_character_id": self.player_character.pk,
                "to_character_id": self.gm_character.pk,
                "item_id": self.item.pk,
                "quantity": 1,
            },
            content_type="application/json",
        )
        money = self.client.post(
            f"/api/campaigns/{self.campaign.pk}/money-transfers/",
            {
                "from_character_id": self.player_character.pk,
                "to_character_id": self.gm_character.pk,
                "amounts": {"gp": 1},
            },
            content_type="application/json",
        )

        self.assertEqual(inventory.status_code, 422)
        self.assertEqual(money.status_code, 422)
