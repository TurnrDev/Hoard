from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from hoard.campaigns.api import armor_values, cast_spell, slot_pools, take_rest
from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterClassLevel,
    CharacterEffect,
    CharacterSpell,
)
from hoard.campaigns.services.cah import parse_cah
from hoard.compendium.models import CompendiumEntry


class CoreModelTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Hoard")
        self.user = get_user_model().objects.create_user(username="jay")

    def test_a_user_can_hold_gm_and_pc_contexts(self) -> None:
        CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )
        pc = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.PC
        )
        Character.objects.create(
            campaign=self.campaign,
            context=pc,
            name="Hero",
            race="Human",
            character_class="Fighter",
            strength=14,
            dexterity=10,
            constitution=12,
            intelligence=8,
            wisdom=10,
            charisma=10,
        )
        with self.assertRaises(IntegrityError):
            CampaignContext.objects.create(
                campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
            )

    def test_campaign_context_role_is_immutable(self) -> None:
        context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )

        context.kind = CampaignContext.Kind.PC

        with self.assertRaises(ValidationError):
            context.save()

    def test_character_requires_a_player_context(self) -> None:
        gm_context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.GM
        )

        with self.assertRaises(ValidationError):
            Character.objects.create(
                campaign=self.campaign,
                context=gm_context,
                name="GM character",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
            )

    def test_campaign_calendar_defaults_and_rollover(self) -> None:
        self.assertEqual(self.campaign.calendar_era_abbreviation, "PD")
        self.assertEqual(self.campaign.calendar_era_name, "Powder Dynasty")
        self.assertEqual(
            (self.campaign.calendar_year, self.campaign.calendar_day), (81, 137)
        )
        self.campaign.calendar_year, self.campaign.calendar_day = 81, 365
        self.campaign.adjust_calendar_day(1)
        self.assertEqual(
            (self.campaign.calendar_year, self.campaign.calendar_day), (82, 1)
        )
        self.campaign.adjust_calendar_day(-1)
        self.assertEqual(
            (self.campaign.calendar_year, self.campaign.calendar_day), (81, 365)
        )

    def test_campaign_calendar_cannot_precede_first_day(self) -> None:
        self.campaign.calendar_year, self.campaign.calendar_day = 1, 1
        with self.assertRaises(ValidationError):
            self.campaign.adjust_calendar_day(-1)

    def test_sheet_derives_modifiers_saves_and_skills(self) -> None:
        character = Character.objects.create(
            campaign=self.campaign,
            name="Hero",
            race="Human",
            character_class="Fighter",
            strength=16,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            strength_save_proficient=True,
            skill_proficiencies={"athletics": "expertise"},
            base_hp=10,
        )
        self.assertEqual(Character.level_for_experience(6500), 5)
        self.assertEqual(character.level, 1)
        self.assertEqual(character.proficiency_bonus, 2)
        self.assertEqual(character.ability_modifier("strength"), 3)
        self.assertEqual(character.max_hp, 12)
        self.assertEqual(character.saving_throw("strength"), 5)
        self.assertEqual(character.skill_bonus("athletics", "strength"), 7)

    def test_spell_slots_casting_and_rests_track_resources_without_dice(self) -> None:
        context = CampaignContext.objects.create(
            campaign=self.campaign, user=self.user, kind=CampaignContext.Kind.PC
        )
        character = Character.objects.create(
            campaign=self.campaign,
            context=context,
            name="Mage",
            race="Human",
            character_class="Wizard",
            strength=8,
            dexterity=12,
            constitution=12,
            intelligence=16,
            wisdom=10,
            charisma=10,
            base_hp=10,
            current_hp=4,
            temporary_hp=3,
        )
        for level in range(1, 4):
            CharacterClassLevel.objects.create(
                character=character, level=level, class_name="Wizard"
            )
        spell = CharacterSpell.objects.create(character=character, name="Shield", level=1)
        character.spell_slot_current = {"1": 2, "2": 2}
        character.save(update_fields=("spell_slot_current",))

        self.assertEqual(slot_pools(character)["1"]["maximum"], 4)
        cast_spell(character, spell.pk, "1", created_by=context)
        character.refresh_from_db()
        self.assertEqual(character.spell_slot_current["1"], 1)

        CharacterEffect.objects.create(
            character=character,
            name="Short-lived ward",
            expires_on_rest=CharacterEffect.RestExpiry.SHORT,
        )
        take_rest(character, "short", 7, created_by=context)
        character.refresh_from_db()
        self.assertEqual(character.current_hp, 7)
        self.assertFalse(character.effects.get(name="Short-lived ward").enabled)

        take_rest(character, "long", None, created_by=context)
        character.refresh_from_db()
        self.assertEqual(character.current_hp, character.max_hp)
        self.assertEqual(character.temporary_hp, 0)
        self.assertEqual(character.spell_slot_current["1"], 4)

    def test_light_armor_uses_base_ac_plus_dexterity(self) -> None:
        armor = CompendiumEntry(
            kind="armor",
            data={"stats": {"base_ac": {"value": 11}, "type": {"value": "light"}}},
        )
        self.assertEqual(armor_values(armor), (11, None))

    def test_cah_parser_warns_for_invalid_optional_values_without_losing_valid_data(
        self,
    ) -> None:
        preview = parse_cah(
            b'{"jsonType":"character","name":"  Hero  ","baseHp":"unknown",'
            b'"baseAc":12,"strength":{"score":14,"scoreModifier":false}}'
        )
        self.assertEqual(preview.fields["name"], "Hero")
        self.assertEqual(preview.fields["strength"], 14)
        self.assertEqual(preview.fields["base_ac"], 12)
        self.assertNotIn("ac_bonus", preview.fields)
        self.assertEqual(preview.warnings, [])

    def test_cah_parser_uses_required_race_name(self) -> None:
        preview = parse_cah(
            b'{"jsonType":"character","race":{"raceId":"fallback"},'
            b'"requiredRace":"{\\"name\\": \\"Displayed race\\"}"}'
        )
        self.assertEqual(preview.fields["race"], "Displayed Race")
