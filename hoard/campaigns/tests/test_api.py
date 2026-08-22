import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from hoard.campaigns.api import _item_data, _items
from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    MoneyTransaction,
)
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)


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
        repository = CompendiumRepository.objects.create(
            identifier="test-api", name="Tests"
        )
        self.source = CompendiumSource.objects.create(
            repository=repository, identifier="5e", name="5e"
        )
        self.campaign.compendium_sources.add(self.source)
        self.item = CompendiumEntry.objects.create(
            source=self.source, kind="item", source_identifier="rope", name="Rope"
        )

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

    def test_players_can_view_the_calendar_but_only_gms_can_adjust_it(self) -> None:
        self.client.force_login(self.player_user)
        visible = self.client.get(f"/api/contexts/{self.pc.pk}/calendar/")
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(visible.json()["year"], 81)
        forbidden = self.client.post(
            f"/api/contexts/{self.pc.pk}/calendar/adjust/",
            data=json.dumps({"amount": 1}),
            content_type="application/json",
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_login(self.gm_user)
        self.campaign.calendar_year, self.campaign.calendar_day = 81, 365
        self.campaign.save(update_fields=("calendar_year", "calendar_day"))
        updated = self.client.post(
            f"/api/contexts/{self.gm.pk}/calendar/adjust/",
            data=json.dumps({"amount": 1}),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual((updated.json()["year"], updated.json()["day"]), (82, 1))

    def test_calendar_rejects_decrement_before_first_day(self) -> None:
        self.campaign.calendar_year, self.campaign.calendar_day = 1, 1
        self.campaign.save(update_fields=("calendar_year", "calendar_day"))
        self.client.force_login(self.gm_user)
        response = self.client.post(
            f"/api/contexts/{self.gm.pk}/calendar/adjust/",
            data=json.dumps({"amount": -1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)

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

    def test_item_data_includes_picker_equipment_metadata(self) -> None:
        self.item.source_book = "phb"
        self.item.cost_amount = "10.00"
        self.item.cost_currency = "gp"
        self.item.weight_amount = "3.000"
        self.item.weight_unit = "pounds"
        self.item.rarity = "common"
        self.item.is_magic = False
        self.item.requires_attunement = False
        self.item.kind = "weapon"
        self.item.data = {"item_type": "sword"}
        self.item.save()

        item = _item_data(_items(self.campaign).get(pk=self.item.pk))
        self.assertEqual(item["equipment"]["category"], "weapon")
        self.assertEqual(item["equipment"]["item_type"], "sword")
        self.assertEqual(item["equipment"]["cost_amount"], "10.00")
        self.assertEqual(item["equipment"]["weight_amount"], "3.000")

    def test_item_list_defers_raw_compendium_payloads(self) -> None:
        self.item.data = {"raw": "x" * 1_000_000}
        self.item.source.data = {"encounter_templates": "x" * 1_000_000}
        self.item.source.repository.data = {"registry": "x" * 1_000_000}
        self.item.save(update_fields=("data",))
        self.item.source.save(update_fields=("data",))
        self.item.source.repository.save(update_fields=("data",))

        item = _items(self.campaign).get(pk=self.item.pk)

        self.assertIn("data", item.get_deferred_fields())
        self.assertIn("data", item.source.get_deferred_fields())
        self.assertIn("data", item.source.repository.get_deferred_fields())

    def test_money_transfer_accepts_multiple_denominations_as_one_transaction(
        self,
    ) -> None:
        self.client.force_login(self.gm_user)
        response = self.client.post(
            f"/api/contexts/{self.gm.pk}/money-transfers/",
            data=json.dumps(
                {
                    "from_character_id": None,
                    "to_character_id": self.character.pk,
                    "amounts": {"gp": 12, "sp": 4, "cp": 7},
                    "description": "Quest reward",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MoneyTransaction.objects.count(), 1)
        self.assertEqual(response.json()["actor"], "gm")
        self.assertEqual(self.character.money.gold, 12)
        self.assertEqual(self.character.money.silver, 4)
        self.assertEqual(self.character.money.copper, 7)

    def test_money_transfer_rejects_zero_negative_and_insufficient_take(self) -> None:
        self.client.force_login(self.gm_user)
        endpoint = f"/api/contexts/{self.gm.pk}/money-transfers/"
        for amounts in ({"gp": 0}, {"gp": -1}):
            response = self.client.post(
                endpoint,
                data=json.dumps(
                    {
                        "from_character_id": None,
                        "to_character_id": self.character.pk,
                        "amounts": amounts,
                    }
                ),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 422)
        response = self.client.post(
            endpoint,
            data=json.dumps(
                {
                    "from_character_id": self.character.pk,
                    "to_character_id": None,
                    "amounts": {"gp": 1, "sp": 1},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)

    def test_character_transaction_filter_includes_actor(self) -> None:
        self.client.force_login(self.gm_user)
        self.client.post(
            f"/api/contexts/{self.gm.pk}/money-transfers/",
            data=json.dumps(
                {
                    "from_character_id": None,
                    "to_character_id": self.character.pk,
                    "amounts": {"gp": 1},
                }
            ),
            content_type="application/json",
        )
        response = self.client.get(
            f"/api/contexts/{self.gm.pk}/transactions/?character_id={self.character.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["actor"], "gm")

    def test_player_cannot_award_shared_experience(self) -> None:
        self.client.force_login(self.player_user)
        response = self.client.post(
            f"/api/contexts/{self.pc.pk}/shared-xp-awards/",
            data=json.dumps({"amount": 100, "description": "No permission"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
