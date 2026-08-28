from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from hoard.campaigns.models import Campaign, CampaignContext, Character, CharacterNote
from hoard.campaigns.services.cah import parse_cah

from .helpers import ContextSocketMixin


class CahImporterTests(SimpleTestCase):
    def test_full_5e_companion_export_preserves_sheet_sections(self) -> None:
        source = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"

        preview = parse_cah(source.read_bytes())

        self.assertEqual(preview.fields["name"], "Hero")
        self.assertEqual(preview.fields["current_hp"], 9)
        self.assertEqual(preview.fields["temporary_hp"], 0)
        self.assertEqual(preview.fields["base_ac"], 10)
        self.assertEqual(preview.fields["background"], "Criminal")
        self.assertEqual(preview.fields["languages"], ["Common", "Choose 1"])
        self.assertEqual(preview.fields["character_class"], "Fighter")
        self.assertEqual(preview.fields["spell_slot_current"]["first"], 0)
        self.assertEqual(len(preview.collections["notes"]), 1)
        self.assertEqual(len(preview.inventory), 7)
        self.assertEqual(preview.inventory[0]["line_id"], "equipment-0")

    def test_rejects_non_character_json(self) -> None:
        with self.assertRaisesMessage(Exception, "5e Companion character"):
            parse_cah(b'{"jsonType": "spell"}')


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CahImportApiTests(ContextSocketMixin, TransactionTestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Test campaign")
        user = get_user_model().objects.create_user(
            username="player", password="secret"
        )
        self.context = CampaignContext.objects.create(
            campaign=self.campaign, user=user, kind=CampaignContext.Kind.PC
        )
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.context,
            is_active=True,
            name="Before",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )
        self.client.force_login(user)

    def test_preview_and_commit_replace_sheet_without_coins_or_xp(self) -> None:
        source = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"
        begun = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.begin",
            character_id=self.character.pk,
        )
        transferred = self.client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", source.read_bytes())},
        )
        self.assertEqual(transferred.status_code, 204)
        preview = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.preview",
            upload_id=begun["data"]["upload_id"],
        )
        draft = preview["data"]
        self.assertNotIn("fields", draft)
        self.assertNotIn("collections", draft)
        self.assertNotIn("raw", draft["inventory"][0])
        self.assertTrue(
            any(change["field"] == "name" for change in draft["field_changes"])
        )
        self.assertTrue(
            any(
                change["collection"] == "notes"
                for change in draft["collection_changes"]
            )
        )
        self.assertEqual(draft["calculated_before"]["max_hp"]["value"], 1)
        self.assertEqual(draft["calculated_after"]["max_hp"]["value"], 9)
        self.assertIn("formula", draft["calculated_after"]["max_hp"])
        self.assertTrue(draft["inventory"])
        committed = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.commit",
            token=draft["token"],
            character_id=self.character.pk,
            inventory=[
                {
                    "line_id": draft["inventory"][0]["line_id"],
                    "action": "add",
                    "quantity": 2,
                }
            ],
        )
        self.assertEqual(committed["type"], "response")
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Hero")
        self.assertEqual(self.character.background, "Criminal")
        self.assertEqual(self.character.experience, 0)
        self.assertEqual(self.character.money.gold, 0)
        self.assertEqual(sum(self.character.inventory.values()), 2)

    def test_commit_allows_field_overrides_and_preserving_sheet_sections(self) -> None:
        source = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"
        CharacterNote.objects.create(
            character=self.character, title="Keep", body="Existing note"
        )
        begun = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.begin",
            character_id=self.character.pk,
        )
        self.client.post(
            begun["data"]["upload_url"],
            {"file": SimpleUploadedFile("hero.cah", source.read_bytes())},
        )
        preview = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.preview",
            upload_id=begun["data"]["upload_id"],
        )["data"]

        committed = self.socket_request(
            self.context.user,
            self.context.pk,
            "characters.imports.cah.commit",
            token=preview["token"],
            character_id=self.character.pk,
            fields={"name": "Adjusted import", "languages": ["Common", "Choose 1"]},
            excluded_fields=["background"],
            collections={"notes": False},
        )

        self.assertEqual(committed["type"], "response")
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Adjusted import")
        self.assertEqual(self.character.background, "")
        self.assertEqual(self.character.languages, ["Common", "Choose 1"])
        self.assertEqual(
            list(self.character.notes.values_list("title", flat=True)), ["Keep"]
        )
