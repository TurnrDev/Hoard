import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase, override_settings

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

from .helpers import ContextSocketMixin


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ContextApiTests(ContextSocketMixin, TransactionTestCase):
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
        contexts = list(
            CampaignContext.objects.filter(user=self.player_user).values_list(
                "kind", flat=True
            )
        )
        self.assertEqual(set(contexts), {"gm", "pc"})

    def test_players_can_view_the_calendar_but_only_gms_can_adjust_it(self) -> None:
        visible = self.socket_request(
            self.player_user, self.pc.pk, "campaign.calendar.get"
        )
        self.assertEqual(visible["data"]["year"], 81)
        forbidden = self.socket_request(
            self.player_user, self.pc.pk, "campaign.calendar.adjust", amount=1
        )
        self.assertEqual(forbidden["type"], "response.error")

        self.campaign.calendar_year, self.campaign.calendar_day = 81, 365
        self.campaign.save(update_fields=("calendar_year", "calendar_day"))
        updated = self.socket_request(
            self.gm_user, self.gm.pk, "campaign.calendar.adjust", amount=1
        )
        self.assertEqual((updated["data"]["year"], updated["data"]["day"]), (82, 1))

    def test_calendar_rejects_decrement_before_first_day(self) -> None:
        self.campaign.calendar_year, self.campaign.calendar_day = 1, 1
        self.campaign.save(update_fields=("calendar_year", "calendar_day"))
        response = self.socket_request(
            self.gm_user, self.gm.pk, "campaign.calendar.adjust", amount=-1
        )
        self.assertEqual(response["type"], "response.error")

    def test_player_cannot_edit_another_character(self) -> None:
        response = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.update",
            character_id=self.character.pk,
            fields={"base_hp": 20},
        )
        self.assertEqual(response["type"], "response")
        self.character.refresh_from_db()
        self.assertEqual(self.character.base_hp, 20)

    def test_cah_preview_does_not_post_ledger_data(self) -> None:
        fixture = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"
        begun = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.imports.cah.begin",
            character_id=self.character.pk,
        )
        self.client.force_login(self.player_user)
        upload = self.client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", fixture.read_bytes())},
        )
        self.assertEqual(upload.status_code, 204)
        preview = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.imports.cah.preview",
            upload_id=begun["data"]["upload_id"],
        )
        committed = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.imports.cah.commit",
            token=preview["data"]["token"],
            character_id=self.character.pk,
        )
        self.assertEqual(committed["type"], "response")
        self.character.refresh_from_db()
        self.assertTrue(self.character.name)
        self.assertGreater(self.character.max_hp, 0)

    def test_cah_byte_transfer_requires_csrf_and_is_single_use(self) -> None:
        begun = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.imports.cah.begin",
            character_id=self.character.pk,
        )
        protected_client = Client(enforce_csrf_checks=True)
        protected_client.force_login(self.player_user)
        denied = protected_client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", b"{}")},
        )
        self.assertEqual(denied.status_code, 403)

        fixture = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"
        self.client.force_login(self.player_user)
        accepted = self.client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", fixture.read_bytes())},
        )
        repeated = self.client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", fixture.read_bytes())},
        )
        self.assertEqual(accepted.status_code, 204)
        self.assertEqual(repeated.status_code, 404)

    def test_transaction_response_has_an_immutable_timestamp(self) -> None:
        response = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "inventory.transactions.create",
            from_character_id=None,
            to_character_id=self.character.pk,
            item_id=self.item.pk,
            quantity=1,
        )
        self.assertEqual(response["type"], "response")
        self.assertIn("occurred_at", response["data"])
        self.assertEqual(response["data"]["campaign_date"], "PD 81, 137th")

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

    def test_builder_definition_is_lightweight_and_loads_selected_entry(self) -> None:
        character_class = CompendiumEntry.objects.create(
            source=self.source,
            kind="class",
            source_identifier="cleric",
            name="Cleric",
            source_book="PHB",
            data={
                "stats": {
                    "archetype_selection_level": {"value": 2},
                    "archetypes": {
                        "value": [
                            {
                                "stats": {
                                    "id": {"value": "life-domain"},
                                    "name": {"value": "Life Domain"},
                                    "source": {"value": "PHB"},
                                },
                                "raw_rules": "x" * 1_100_000,
                            }
                        ]
                    }
                }
            },
        )

        definition = self.socket_request(
            self.player_user, self.pc.pk, "characters.builder.definition"
        )

        self.assertEqual(definition["type"], "response")
        self.assertLess(len(json.dumps(definition).encode()), 100_000)
        class_row = next(
            row
            for row in definition["data"]["class"]
            if row["id"] == character_class.pk
        )
        self.assertNotIn("data", class_row)
        self.assertEqual(class_row["source_book"], "PHB")
        self.assertEqual(class_row["repository"], "Tests")

        detail = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.builder.entry.get",
            entry_id=character_class.pk,
        )
        self.assertEqual(detail["data"]["data"]["subchoices"], ["Life Domain"])
        self.assertEqual(detail["data"]["data"]["subclass_selection_level"], 2)
        self.assertEqual(
            detail["data"]["data"]["subclasses"],
            [
                {
                    "identifier": "life-domain",
                    "name": "Life Domain",
                    "source": "PHB",
                    "level": 2,
                }
            ],
        )
        self.assertNotIn("raw_rules", json.dumps(detail))

    def test_builder_definition_collapses_republished_system_entries(self) -> None:
        canonical = CompendiumEntry.objects.create(
            source=self.source,
            kind="class",
            source_identifier="ranger",
            name="Ranger",
            source_book="PHB",
        )
        dependency_repository = CompendiumRepository.objects.create(
            identifier="github:example/setting", name="Setting dependency"
        )
        dependency_source = CompendiumSource.objects.create(
            repository=dependency_repository, identifier="5e", name="5e"
        )
        self.campaign.compendium_sources.add(dependency_source)
        CompendiumEntry.objects.create(
            source=dependency_source,
            kind="class",
            source_identifier="ranger",
            name="Ranger",
            source_book="PHB",
        )

        definition = self.socket_request(
            self.player_user, self.pc.pk, "characters.builder.definition"
        )
        rangers = [
            row for row in definition["data"]["class"] if row["name"] == "Ranger"
        ]

        self.assertEqual(len(rangers), 1)
        self.assertEqual(rangers[0]["id"], canonical.pk)
        self.assertEqual(rangers[0]["source_book"], "PHB")
        self.assertEqual(len(rangers[0]["alias_ids"]), 1)

    def test_builder_class_defaults_subclass_selection_to_level_three(self) -> None:
        character_class = CompendiumEntry.objects.create(
            source=self.source,
            kind="class",
            source_identifier="ranger",
            name="Ranger",
            data={
                "stats": {
                    "archetypes": {
                        "value": [
                            {
                                "stats": {
                                    "id": {"value": "hunter"},
                                    "name": {"value": "Hunter"},
                                }
                            }
                        ]
                    }
                }
            },
        )

        detail = self.socket_request(
            self.player_user,
            self.pc.pk,
            "characters.builder.entry.get",
            entry_id=character_class.pk,
        )

        self.assertEqual(detail["data"]["data"]["subclass_selection_level"], 3)
        self.assertEqual(detail["data"]["data"]["subclasses"][0]["level"], 3)

    def test_money_transfer_accepts_multiple_denominations_as_one_transaction(
        self,
    ) -> None:
        response = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "money.transfers.create",
            from_character_id=None,
            to_character_id=self.character.pk,
            amounts={"gp": 12, "sp": 4, "cp": 7},
            description="Quest reward",
        )
        self.assertEqual(response["type"], "response")
        self.assertEqual(MoneyTransaction.objects.count(), 1)
        self.assertEqual(response["data"]["actor"], "gm")
        self.assertEqual(self.character.money.gold, 12)
        self.assertEqual(self.character.money.silver, 4)
        self.assertEqual(self.character.money.copper, 7)

    def test_money_transfer_rejects_zero_negative_and_insufficient_take(self) -> None:
        for amounts in ({"gp": 0}, {"gp": -1}):
            response = self.socket_request(
                self.gm_user,
                self.gm.pk,
                "money.transfers.create",
                from_character_id=None,
                to_character_id=self.character.pk,
                amounts=amounts,
            )
            self.assertEqual(response["type"], "response.error")
        response = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "money.transfers.create",
            from_character_id=self.character.pk,
            to_character_id=None,
            amounts={"gp": 1, "sp": 1},
        )
        self.assertEqual(response["type"], "response.error")

    def test_character_transaction_filter_includes_actor(self) -> None:
        self.socket_request(
            self.gm_user,
            self.gm.pk,
            "money.transfers.create",
            from_character_id=None,
            to_character_id=self.character.pk,
            amounts={"gp": 1},
        )
        response = self.socket_request(
            self.gm_user,
            self.gm.pk,
            "transactions.list",
            character_id=self.character.pk,
        )
        self.assertEqual(response["data"]["count"], 1)
        self.assertEqual(response["data"]["results"][0]["actor"], "gm")

    def test_player_cannot_award_shared_experience(self) -> None:
        response = self.socket_request(
            self.player_user,
            self.pc.pk,
            "experience.shared_awards.create",
            amount=100,
            description="No permission",
        )
        self.assertEqual(response["type"], "response.error")
