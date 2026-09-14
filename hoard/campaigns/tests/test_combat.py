from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext, ConditionEvent
from hoard.campaigns.services.combat import (
    add_character_combatant,
    add_encounter_combatant,
    encounter_data,
    finish_encounter,
    remove_character_condition,
    set_character_condition,
    set_combatant_condition,
    start_encounter,
)

from .helpers import make_character


class EncounterServiceTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Combat test")
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="gm"),
            kind=CampaignContext.Kind.GM,
        )
        self.player = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="player"),
            kind=CampaignContext.Kind.PC,
        )
        self.hero = make_character(
            self.campaign,
            name="Hero",
            active=True,
            context=self.player,
        )

    def test_start_enrols_active_players_and_keeps_one_active_encounter(self) -> None:
        make_character(self.campaign, name="Inactive", active=False)

        encounter = start_encounter(self.gm)
        repeated = start_encounter(self.gm)

        self.assertEqual(repeated, encounter)
        combatant = encounter.combatants.get()
        self.assertEqual(combatant.character, self.hero)
        self.assertEqual(combatant.initiative, 0)

        second_position = add_character_combatant(self.gm, self.hero.pk, 8)
        self.assertEqual(second_position.character, self.hero)
        self.assertEqual(encounter.combatants.filter(character=self.hero).count(), 2)

        finish_encounter(self.gm)
        encounter.refresh_from_db()
        self.assertFalse(encounter.is_active)
        self.assertIsNotNone(encounter.ended_at)

    def test_players_cannot_manage_encounters(self) -> None:
        with self.assertRaises(PermissionError):
            start_encounter(self.player)

    def test_hidden_monster_health_is_filtered_for_players(self) -> None:
        start_encounter(self.gm)
        monster = add_encounter_combatant(
            self.gm,
            name="Bog beast",
            creature_entry_id=None,
            initiative=14,
            current_hp=23,
            max_hp=40,
            show_hp_bar=False,
            show_hp_numbers=False,
        )

        gm_monster = next(
            row
            for row in encounter_data(self.gm)["combatants"]
            if row["id"] == monster.pk
        )
        player_monster = next(
            row
            for row in encounter_data(self.player)["combatants"]
            if row["id"] == monster.pk
        )

        self.assertEqual(gm_monster["current_hp"], 23)
        self.assertEqual(gm_monster["health_percentage"], 58)
        self.assertIsNone(player_monster["current_hp"])
        self.assertIsNone(player_monster["max_hp"])
        self.assertIsNone(player_monster["health_percentage"])

    def test_conditions_are_structured_and_exhaustion_requires_a_level(self) -> None:
        encounter = start_encounter(self.gm)
        combatant = encounter.combatants.get(character=self.hero)
        set_combatant_condition(
            self.gm,
            combatant.pk,
            identifier="pacify",
            source="Obojima",
            duration="Until the next turn",
            exhaustion_level=None,
        )

        condition = encounter_data(self.player)["combatants"][0]["conditions"][0]
        self.assertEqual(condition["id"], "pacify")
        self.assertEqual(condition["source"], "Obojima")
        self.assertEqual(len(condition["instances"]), 1)

        with self.assertRaises(ValidationError):
            set_combatant_condition(
                self.gm,
                combatant.pk,
                identifier="exhaustion",
                source="",
                duration="",
                exhaustion_level=None,
            )

        finish_encounter(self.gm)
        self.assertTrue(self.hero.conditions.filter(identifier="pacify").exists())

        next_encounter = start_encounter(self.gm)
        next_condition = encounter_data(self.player)["combatants"][0]["conditions"][0]
        self.assertNotEqual(next_encounter, encounter)
        self.assertEqual(next_condition["id"], "pacify")

    def test_owner_can_manage_character_condition_outside_combat(self) -> None:
        condition = set_character_condition(
            self.player,
            self.hero.pk,
            identifier="exhaustion",
            source="Hunger",
            duration="Until fed and rested",
            exhaustion_level=1,
        )

        self.assertEqual(condition.character, self.hero)
        self.assertEqual(condition.exhaustion_level, 1)

        remove_character_condition(
            self.player,
            self.hero.pk,
            identifier="exhaustion",
        )
        self.assertFalse(self.hero.conditions.exists())

    def test_condition_causes_are_independent_but_display_as_one_condition(
        self,
    ) -> None:
        first = set_character_condition(
            self.player,
            self.hero.pk,
            identifier="restrained",
            source="Entangle",
            duration="Concentration",
            exhaustion_level=None,
        )
        second = set_character_condition(
            self.player,
            self.hero.pk,
            identifier="restrained",
            source="Giant spider web",
            duration="Until escaped",
            exhaustion_level=None,
        )

        start_encounter(self.gm)
        condition = encounter_data(self.player)["combatants"][0]["conditions"][0]
        self.assertEqual(condition["id"], "restrained")
        self.assertEqual(
            [instance["id"] for instance in condition["instances"]],
            [first.pk, second.pk],
        )

        remove_character_condition(
            self.player,
            self.hero.pk,
            condition_id=first.pk,
        )

        self.assertTrue(self.hero.conditions.filter(pk=second.pk).exists())
        self.assertEqual(ConditionEvent.objects.count(), 3)
        self.assertEqual(
            list(ConditionEvent.objects.values_list("action", flat=True)),
            ["removed", "applied", "applied"],
        )

    def test_exhaustion_updates_one_levelled_condition(self) -> None:
        condition = set_character_condition(
            self.player,
            self.hero.pk,
            identifier="exhaustion",
            source="Hunger",
            duration="Until fed and rested",
            exhaustion_level=1,
        )
        updated = set_character_condition(
            self.player,
            self.hero.pk,
            identifier="exhaustion",
            source="Hunger",
            duration="Until fed and rested",
            exhaustion_level=2,
        )

        self.assertEqual(updated.pk, condition.pk)
        self.assertEqual(self.hero.conditions.count(), 1)
        self.assertEqual(
            list(ConditionEvent.objects.values_list("action", flat=True)),
            ["updated", "applied"],
        )
