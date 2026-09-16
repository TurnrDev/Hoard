from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, CampaignContext
from hoard.campaigns.services.combat import (
    add_character_combatant,
    add_encounter_combatant,
    choose_initiative_tie,
    encounter_data,
    end_player_turn,
    finish_encounter,
    reorder_combatants,
    roll_player_initiative,
    set_current_combatant,
    start_encounter,
)

from .helpers import make_character


class EncounterServiceTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(name="Combat test")
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="combat-gm"),
            kind=CampaignContext.Kind.GM,
        )
        self.player = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username="combat-player"),
            kind=CampaignContext.Kind.PC,
        )
        self.hero = make_character(
            self.campaign,
            name="Hero",
            active=True,
            context=self.player,
        )

    def add_other_player(self, name: str = "Other"):
        context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=get_user_model().objects.create_user(username=name.lower()),
            kind=CampaignContext.Kind.PC,
        )
        character = make_character(
            self.campaign,
            name=name,
            active=True,
            context=context,
        )

        return context, character

    def test_start_enrols_active_players_and_finishes_the_encounter(self) -> None:
        make_character(self.campaign, name="Inactive", active=False)

        encounter = start_encounter(self.gm)

        self.assertEqual(start_encounter(self.gm), encounter)
        combatant = encounter.combatants.get()
        self.assertEqual(combatant.character, self.hero)
        self.assertEqual(combatant.initiative_modifier, self.hero.initiative_bonus)
        self.assertEqual(encounter.started_by, self.gm)

        finish_encounter(self.gm)
        encounter.refresh_from_db()
        self.assertFalse(encounter.is_active)
        self.assertIsNotNone(encounter.ended_at)

    def test_only_game_masters_can_manage_combat(self) -> None:
        with self.assertRaises(PermissionError):
            start_encounter(self.player)

        encounter = start_encounter(self.gm)
        combatant = encounter.combatants.get()
        with self.assertRaises(PermissionError):
            set_current_combatant(self.player, combatant.pk)

    def test_player_roll_uses_calculated_initiative_and_can_end_turn(self) -> None:
        self.hero.dexterity = 14
        self.hero.jack_of_all_trades = True
        self.hero.initiative_adjustment = 1
        self.hero.save()
        encounter = start_encounter(self.gm)

        combatant = roll_player_initiative(self.player, 12)

        self.assertEqual(combatant.initiative_modifier, 4)
        self.assertEqual(combatant.initiative, 16)
        set_current_combatant(self.gm, combatant.pk)
        end_player_turn(self.player)
        encounter.refresh_from_db()
        self.assertEqual(encounter.current_combatant_id, combatant.pk)

        with self.assertRaises(ValidationError):
            roll_player_initiative(self.player, 10)

    def test_natural_twenty_grants_exactly_one_bonus_initiative(self) -> None:
        encounter = start_encounter(self.gm)

        first = roll_player_initiative(self.player, 20)
        second = encounter.combatants.exclude(pk=first.pk).get()
        self.assertIsNone(second.initiative_roll)

        roll_player_initiative(self.player, 20)
        self.assertEqual(encounter.combatants.filter(character=self.hero).count(), 2)

    def test_exact_tie_uses_agreement_or_persisted_random_choice(self) -> None:
        other_context, _ = self.add_other_player()
        start_encounter(self.gm)
        hero_entry = roll_player_initiative(self.player, 10)
        other_entry = roll_player_initiative(other_context, 10)

        choose_initiative_tie(self.player, other_entry.pk)
        choose_initiative_tie(other_context, other_entry.pk)
        agreed = encounter_data(self.player)
        assert agreed is not None
        hero_row = next(row for row in agreed["combatants"] if row["id"] == hero_entry.pk)
        self.assertEqual(hero_row["tie_resolution"], "agreement")
        self.assertEqual(hero_row["tie_winner_id"], other_entry.pk)

        encounter = start_encounter(self.gm)
        encounter.initiative_tie_choices = {}
        encounter.initiative_tie_breaks = {}
        encounter.save()
        choose_initiative_tie(self.player, hero_entry.pk)
        with patch("hoard.campaigns.services.combat.choice", return_value=other_entry.pk):
            choose_initiative_tie(other_context, other_entry.pk)
        random_result = encounter_data(self.player)
        assert random_result is not None
        hero_row = next(
            row for row in random_result["combatants"] if row["id"] == hero_entry.pk
        )
        self.assertEqual(hero_row["tie_resolution"], "random")

    def test_custom_combatant_health_is_hidden_as_a_percentage(self) -> None:
        start_encounter(self.gm)
        monster = add_encounter_combatant(
            self.gm,
            name="Bog beast",
            initiative=14,
            current_hp=23,
            max_hp=40,
        )

        gm_data = encounter_data(self.gm)
        player_data = encounter_data(self.player)
        assert gm_data is not None and player_data is not None
        gm_row = next(row for row in gm_data["combatants"] if row["id"] == monster.pk)
        player_row = next(
            row for row in player_data["combatants"] if row["id"] == monster.pk
        )
        self.assertEqual(gm_row["current_hp"], 23)
        self.assertEqual(player_row["current_hp"], 58)
        self.assertEqual(player_row["max_hp"], 100)

    def test_reorder_and_duplicate_character_entries(self) -> None:
        encounter = start_encounter(self.gm)
        first = encounter.combatants.get()
        second = add_character_combatant(self.gm, self.hero.pk, 8)
        custom = add_encounter_combatant(
            self.gm,
            name="Goblin",
            initiative=6,
            current_hp=None,
            max_hp=None,
        )

        reordered = reorder_combatants(self.gm, [custom.pk, first.pk, second.pk])

        self.assertEqual([row.pk for row in reordered], [custom.pk, first.pk, second.pk])
        self.assertEqual([row.initiative for row in reordered], [8, 6, 0])
        with self.assertRaises(ValidationError):
            reorder_combatants(self.gm, [first.pk])
