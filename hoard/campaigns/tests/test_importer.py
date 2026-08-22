from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from hoard.campaigns.models import Campaign, CampaignContext, Character
from hoard.campaigns.services.cah import parse_cah


class CahImporterTests(SimpleTestCase):
    def test_full_5e_companion_export_preserves_sheet_sections(self) -> None:
        source = Path(__file__).with_name("fixtures") / "5e_companion_minimal.cah"

        preview = parse_cah(source.read_bytes())

        self.assertEqual(preview.fields["name"], "Hero")
        self.assertEqual(preview.fields["current_hp"], 9)
        self.assertEqual(preview.fields["temporary_hp"], 0)
        self.assertEqual(preview.fields["base_ac"], 10)
        self.assertEqual(preview.fields["background"], "Criminal")
        self.assertEqual(preview.fields["character_class"], "Fighter")
        self.assertEqual(preview.fields["spell_slots"]["first"], 0)
        self.assertEqual(len(preview.collections["notes"]), 1)
        self.assertEqual(len(preview.inventory), 7)
        self.assertEqual(preview.inventory[0]["line_id"], "equipment-0")

    def test_rejects_non_character_json(self) -> None:
        with self.assertRaisesMessage(Exception, "5e Companion character"):
            parse_cah(b'{"jsonType": "spell"}')


class CahImportApiTests(TestCase):
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
        preview = self.client.post(
            f"/api/contexts/{self.context.pk}/character-imports/cah/preview?character_id={self.character.pk}",
            {"file": SimpleUploadedFile("hero.cah", source.read_bytes())},
        )
        self.assertEqual(preview.status_code, 200)
        draft = preview.json()
        self.assertEqual(draft["calculated_before"]["max_hp"], 1)
        self.assertEqual(draft["calculated_after"]["max_hp"], 9)
        self.assertTrue(draft["inventory"])
        committed = self.client.post(
            f"/api/contexts/{self.context.pk}/character-imports/cah/commit",
            data=json.dumps(
                {
                    "token": draft["token"],
                    "character_id": self.character.pk,
                    "inventory": [
                        {
                            "line_id": draft["inventory"][0]["line_id"],
                            "action": "add",
                            "quantity": 2,
                        }
                    ],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(committed.status_code, 200)
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Hero")
        self.assertEqual(self.character.background, "Criminal")
        self.assertEqual(self.character.experience, 0)
        self.assertEqual(self.character.money.gold, 0)
        self.assertEqual(sum(self.character.inventory.values()), 2)
