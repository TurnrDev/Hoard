from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterNativeEvent,
)
from hoard.campaigns.services.native import (
    HOARD_RENDERED_SHEET_SECTIONS,
    execute_character_event,
    native_sheet_view,
)
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)


class NativeCharacterRuntimeTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Native campaign")
        user = get_user_model().objects.create_user(username="native-player")
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=user,
            kind=CampaignContext.Kind.PC,
        )
        repository = CompendiumRepository.objects.create(
            identifier="native-test-default",
            name="Default",
        )
        self.source = CompendiumSource.objects.create(
            repository=repository,
            identifier="5e",
            name="5e",
            version="0.9.0",
            package_checksum="a" * 64,
            system_definition={
                "id": "5e",
                "version": "0.9.0",
                "character_stats": [
                    {
                        "id": "name",
                        "type": "base",
                        "value_type": "string",
                        "default_value": "",
                    },
                    {
                        "id": "base_hp",
                        "type": "base",
                        "value_type": "integer",
                        "default_value": 1,
                    },
                    {
                        "id": "current_hp",
                        "type": "base",
                        "value_type": "integer",
                        "default_value": 1,
                    },
                    *[
                        {
                            "id": f"{ability}_score",
                            "type": "base",
                            "value_type": "integer",
                            "default_value": 8,
                        }
                        for ability in (
                            "strength",
                            "dexterity",
                            "constitution",
                            "intelligence",
                            "wisdom",
                            "charisma",
                        )
                    ],
                ],
            },
        )
        self.campaign.compendium_sources.add(self.source)
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.context,
            name="Native hero",
            strength=12,
            dexterity=10,
            constitution=14,
            intelligence=8,
            wisdom=10,
            charisma=10,
            base_hp=10,
            current_hp=7,
            native_system_source=self.source,
        )

    def test_executes_persists_projects_and_audits_atomically(self) -> None:
        result = execute_character_event(
            self.character,
            "hoard.damage",
            {"amount": 3},
            created_by=self.context,
            effects={
                "type": "addToStat",
                "stat": "current_hp",
                "value": {"type": "constant", "value": -3},
                "aggregation_type": "set",
            },
        )

        self.character.refresh_from_db()
        self.assertEqual(self.character.current_hp, 4)
        self.assertEqual(self.character.native_state["current_hp"], 4)
        self.assertEqual(self.character.native_system_version, "0.9.0")
        event = CharacterNativeEvent.objects.get()
        self.assertEqual(event, result.event)
        self.assertEqual(event.payload, {"amount": 3})
        self.assertEqual(event.system_checksum, "a" * 64)
        self.assertEqual(event.changes[0]["after"], 4)

    def test_rejects_a_disabled_native_system_source(self) -> None:
        self.campaign.compendium_sources.clear()

        with self.assertRaisesMessage(ValidationError, "No installed 5e"):
            execute_character_event(self.character, "anything")

    def test_resolves_native_views_and_exposes_control_behaviour(self) -> None:
        definition = self.source.system_definition
        definition["character_sheet_sections"] = [
            {
                "id": "extension",
                "view": {
                    "type": "section",
                    "id": "extension_section",
                    "content": [
                        {
                            "type": "text",
                            "id": "current_health",
                            "text": {"type": "stat", "stat": "current_hp"},
                        },
                        {
                            "type": "button",
                            "id": "extension_action",
                            "title": {"type": "constant", "value": "Use"},
                            "event": {"name": "use_extension"},
                        },
                    ],
                },
            }
        ]
        self.source.system_definition = definition
        self.source.save(update_fields=("system_definition",))

        sheet = native_sheet_view(self.character)

        content = sheet["sections"][0]["view"]["content"]
        self.assertEqual(content[0]["text"]["value"], 7)
        self.assertEqual(
            content[1]["system_behaviour"]["event"], {"name": "use_extension"}
        )

    def test_omits_sections_rendered_by_hoard_from_character_payloads(self) -> None:
        definition = self.source.system_definition
        definition["character_sheet_sections"] = [
            {"id": "abilities", "view": {"type": "section", "id": "abilities"}},
            {
                "id": "campaign_extension",
                "view": {
                    "type": "section",
                    "id": "campaign_extension",
                    "content": [
                        {
                            "type": "text",
                            "id": "extension_text",
                            "text": "Extension",
                        }
                    ],
                },
            },
        ]
        self.source.system_definition = definition
        self.source.save(update_fields=("system_definition",))

        sheet = native_sheet_view(
            self.character,
            excluded_section_ids=HOARD_RENDERED_SHEET_SECTIONS,
        )

        self.assertEqual(
            [section["id"] for section in sheet["sections"]],
            ["campaign_extension"],
        )

    def test_class_details_are_the_native_multiclass_authority(self) -> None:
        from hoard.campaigns.services.native import (
            native_class_details,
            native_class_level,
            native_class_summary,
        )

        fighter = CompendiumEntry.objects.create(
            source=self.source,
            kind=CompendiumEntry.Kind.CLASS,
            source_identifier="fighter",
            name="Fighter",
            data={
                "resource_id": "class",
                "stats": {"name": {"value": "Fighter"}},
            },
        )
        wizard = CompendiumEntry.objects.create(
            source=self.source,
            kind=CompendiumEntry.Kind.CLASS,
            source_identifier="wizard",
            name="Wizard",
            data={
                "resource_id": "class",
                "stats": {"name": {"value": "Wizard"}},
            },
        )

        state = {
            "classes": [
                native_class_details(fighter, class_level=2),
                native_class_details(wizard, class_level=1),
            ]
        }

        self.assertEqual(native_class_level(state), 3)
        self.assertEqual(native_class_summary(state), "Fighter 2 / Wizard 1")
