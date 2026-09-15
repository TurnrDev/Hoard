from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext, ConditionEvent
from hoard.campaigns.services.combat import (
    add_character_combatant,
    add_encounter_combatant,
    choose_initiative_tie,
    encounter_data,
    end_player_turn,
    finish_encounter,
    remove_character_condition,
    reorder_combatants,
    roll_player_initiative,
    set_character_condition,
    set_combatant_condition,
    set_current_combatant,
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
        self.assertTrue(second_position.show_hp_numbers)
        self.assertEqual(encounter.combatants.filter(character=self.hero).count(), 2)

        set_current_combatant(self.gm, second_position.pk)
        encounter.refresh_from_db()
        self.assertEqual(encounter.current_combatant, second_position)
        self.assertEqual(
            encounter_data(self.player)["current_combatant_id"],
            second_position.pk,
        )

        non_player_character = make_character(
            self.campaign,
            name="Guide",
            active=True,
            context=False,
        )
        guide_position = add_character_combatant(
            self.gm,
            non_player_character.pk,
            6,
        )
        self.assertFalse(guide_position.show_hp_numbers)

        reordered = reorder_combatants(
            self.gm,
            [guide_position.pk, combatant.pk, second_position.pk],
        )
        self.assertEqual(
            [(entry.pk, entry.initiative) for entry in reordered],
            [
                (guide_position.pk, 8),
                (combatant.pk, 6),
                (second_position.pk, 0),
            ],
        )

        with self.assertRaises(ValidationError):
            reorder_combatants(self.gm, [combatant.pk])

        finish_encounter(self.gm)
        encounter.refresh_from_db()
        self.assertFalse(encounter.is_active)
        self.assertIsNotNone(encounter.ended_at)
        self.assertIsNone(encounter.current_combatant)

    def test_players_cannot_manage_encounters(self) -> None:
        with self.assertRaises(PermissionError):
            start_encounter(self.player)

        encounter = start_encounter(self.gm)
        combatant = encounter.combatants.get()
        with self.assertRaises(PermissionError):
            set_current_combatant(self.player, combatant.pk)

    def test_player_rolls_bare_initiative_and_ends_only_their_turn(self) -> None:
        self.hero.dexterity = 16
        self.hero.save(update_fields=("dexterity",))
        encounter = start_encounter(self.gm)

        combatant = roll_player_initiative(self.player, 12)

        self.assertEqual(combatant.initiative_roll, 12)
        self.assertEqual(combatant.initiative_modifier, 3)
        self.assertEqual(combatant.initiative, 15)
        set_current_combatant(self.gm, combatant.pk)
        end_player_turn(self.player)
        encounter.refresh_from_db()
        self.assertEqual(encounter.current_combatant_id, combatant.pk)

        with self.assertRaises(ValidationError):
            roll_player_initiative(self.player, 10)

    def test_natural_twenty_grants_exactly_one_second_initiative(self) -> None:
        encounter = start_encounter(self.gm)

        first = roll_player_initiative(self.player, 20)
        second = encounter.combatants.exclude(pk=first.pk).get()
        self.assertIsNone(second.initiative_roll)

        rolled_second = roll_player_initiative(self.player, 20)
        self.assertEqual(rolled_second.pk, second.pk)
        self.assertEqual(encounter.combatants.filter(character=self.hero).count(), 2)

        with self.assertRaises(ValidationError):
            roll_player_initiative(self.player, 1)

    def test_exact_tie_uses_player_agreement(self) -> None:
        other_context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="other"),
            kind=CampaignContext.Kind.PC,
        )
        make_character(
            self.campaign,
            name="Other",
            active=True,
            context=other_context,
        )
        start_encounter(self.gm)
        hero_entry = roll_player_initiative(self.player, 10)
        other_entry = roll_player_initiative(other_context, 10)

        default_order = [row["id"] for row in encounter_data(self.gm)["combatants"]]
        self.assertIn(default_order[0], (hero_entry.pk, other_entry.pk))

        choose_initiative_tie(self.player, other_entry.pk)
        player_rows = encounter_data(self.player)["combatants"]
        player_tie = next(row for row in player_rows if row["id"] == hero_entry.pk)
        vote_counts = {
            option["combatant_id"]: option["vote_count"]
            for option in player_tie["tie_options"]
        }
        self.assertEqual(player_tie["tie_votes_cast"], 1)
        self.assertEqual(player_tie["tie_votes_required"], 2)
        self.assertEqual(player_tie["tie_winner_id"], None)
        self.assertEqual(player_tie["tie_resolution"], None)
        self.assertEqual(vote_counts[other_entry.pk], 1)

        choose_initiative_tie(other_context, other_entry.pk)
        agreed_rows = encounter_data(self.gm)["combatants"]
        agreed_order = [row["id"] for row in agreed_rows]
        self.assertEqual(agreed_order[0], other_entry.pk)
        self.assertEqual(
            [row["initiative_position"] for row in agreed_rows],
            list(range(len(agreed_rows))),
        )

        resolved_rows = encounter_data(self.player)["combatants"]
        resolved_tie = next(row for row in resolved_rows if row["id"] == hero_entry.pk)
        resolved_counts = {
            option["combatant_id"]: option["vote_count"]
            for option in resolved_tie["tie_options"]
        }
        self.assertEqual(resolved_tie["tie_votes_cast"], 2)
        self.assertEqual(resolved_tie["tie_winner_id"], other_entry.pk)
        self.assertEqual(resolved_tie["tie_resolution"], "agreement")
        self.assertEqual(resolved_counts[other_entry.pk], 2)

    def test_exact_tie_randomly_resolves_only_after_disagreement(self) -> None:
        other_context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="other-random"),
            kind=CampaignContext.Kind.PC,
        )
        make_character(
            self.campaign,
            name="Other Random",
            active=True,
            context=other_context,
        )
        start_encounter(self.gm)
        hero_entry = roll_player_initiative(self.player, 10)
        other_entry = roll_player_initiative(other_context, 10)

        choose_initiative_tie(self.player, hero_entry.pk)
        partial_rows = encounter_data(self.player)["combatants"]
        partial_tie = next(row for row in partial_rows if row["id"] == hero_entry.pk)
        self.assertEqual(partial_tie["tie_votes_cast"], 1)
        self.assertEqual(partial_tie["tie_winner_id"], None)
        self.assertEqual(partial_tie["tie_resolution"], None)

        with patch(
            "hoard.campaigns.services.combat.choice",
            return_value=other_entry.pk,
        ):
            choose_initiative_tie(other_context, other_entry.pk)

        resolved_rows = encounter_data(self.player)["combatants"]
        resolved_tie = next(row for row in resolved_rows if row["id"] == hero_entry.pk)
        resolved_order = [row["id"] for row in encounter_data(self.gm)["combatants"]]
        self.assertEqual(resolved_tie["tie_votes_cast"], 2)
        self.assertEqual(resolved_tie["tie_winner_id"], other_entry.pk)
        self.assertEqual(resolved_tie["tie_resolution"], "random")
        self.assertEqual(resolved_order[0], other_entry.pk)

    def test_equal_results_put_the_higher_dexterity_modifier_first(self) -> None:
        other_context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="quicker"),
            kind=CampaignContext.Kind.PC,
        )
        other = make_character(
            self.campaign,
            name="Quicker",
            active=True,
            context=other_context,
        )
        other.dexterity = 12
        other.save(update_fields=("dexterity",))
        start_encounter(self.gm)
        roll_player_initiative(self.player, 10)
        quicker_entry = roll_player_initiative(other_context, 9)

        order = [row["id"] for row in encounter_data(self.gm)["combatants"]]

        self.assertEqual(order[0], quicker_entry.pk)

    def test_monster_health_is_normalized_for_players(self) -> None:
        start_encounter(self.gm)
        monster = add_encounter_combatant(
            self.gm,
            name="Bog beast",
            creature_entry_id=None,
            initiative=14,
            current_hp=23,
            max_hp=40,
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
        self.assertEqual(player_monster["current_hp"], 58)
        self.assertEqual(player_monster["max_hp"], 100)
        self.assertEqual(player_monster["health_percentage"], 58)

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
