from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext, Character
from hoard.campaigns.services.cah import parse_cah


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

    def test_cah_parser_warns_for_invalid_optional_values_without_losing_valid_data(
        self,
    ) -> None:
        preview = parse_cah(
            b'{"jsonType":"character","name":"  Hero  ","baseHp":"unknown",'
            b'"baseAc":12,"strength":{"score":14,"scoreModifier":false}}'
        )
        self.assertEqual(preview.fields["name"], "Hero")
        self.assertEqual(preview.fields["strength"], 14)
        self.assertNotIn("base_ac", preview.fields)
        self.assertNotIn("ac_bonus", preview.fields)
        self.assertTrue(any("Base HP" in warning for warning in preview.warnings))

    def test_cah_parser_uses_required_race_name(self) -> None:
        preview = parse_cah(
            b'{"jsonType":"character","race":{"raceId":"fallback"},'
            b'"requiredRace":"{\\"name\\": \\"Displayed race\\"}"}'
        )
        self.assertEqual(preview.fields["race"], "Displayed race")
