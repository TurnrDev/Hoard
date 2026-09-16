from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from hoard.campaigns.models import Campaign, Character


class CharacterStatisticTests(SimpleTestCase):
    def character(self, **values) -> Character:
        defaults = {
            "campaign": Campaign(name="Statistics", level=5),
            "name": "Hero",
        }
        defaults.update(values)
        return Character(**defaults)

    def test_ability_score_uses_every_stored_component(self) -> None:
        character = self.character(
            strength=12,
            ability_bonuses={"strength": 2},
            background_ability_bonuses={"strength": 1},
            ability_score_adjustments={"strength": -1},
        )

        self.assertEqual(character.ability_score("strength"), 14)
        self.assertEqual(character.ability_modifier("strength"), 2)

    def test_proficiency_adjustment_applies_to_skills_and_saves(self) -> None:
        character = self.character(
            proficiency_bonus_adjustment=1,
            dexterity=14,
            skill_proficiencies={"stealth": "expertise"},
            skill_adjustments={"stealth": 1},
            save_proficiencies={"dexterity": "proficient"},
            save_adjustments={"dexterity": -1},
        )

        self.assertEqual(character.proficiency_bonus, 4)
        self.assertEqual(character.skill_bonus("stealth", "dexterity"), 11)
        self.assertEqual(character.saving_throw("dexterity"), 5)

    def test_jack_of_all_trades_rounds_down(self) -> None:
        character = self.character(jack_of_all_trades=True)

        self.assertEqual(character.half_proficiency("wisdom", "none"), 1)
        self.assertEqual(character.ability_check("wisdom"), 1)
        self.assertEqual(character.half_proficiency("wisdom", "proficient"), 0)

    def test_remarkable_athlete_rounds_up_only_for_eligible_checks(self) -> None:
        character = self.character(remarkable_athlete=True)

        self.assertEqual(character.half_proficiency("dexterity", "none"), 2)
        self.assertEqual(character.half_proficiency("wisdom", "none"), 0)
        self.assertEqual(character.initiative_bonus, 2)

    def test_half_proficiency_features_use_larger_value_without_stacking(self) -> None:
        character = self.character(
            jack_of_all_trades=True,
            remarkable_athlete=True,
        )

        self.assertEqual(character.half_proficiency("strength", "none"), 2)

    def test_max_hp_uses_rolled_hp_constitution_per_level_and_custom(self) -> None:
        character = self.character(
            rolled_hit_points=20,
            constitution=14,
            hp_adjustment=3,
        )

        self.assertEqual(character.max_hp, 33)

    def test_invalid_proficiency_states_are_rejected(self) -> None:
        character = self.character(
            skill_proficiencies={"stealth": "half"},
            save_proficiencies={"dexterity": "expertise"},
        )

        with self.assertRaises(ValidationError):
            character.full_clean()
