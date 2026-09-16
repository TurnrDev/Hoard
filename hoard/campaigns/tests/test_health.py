from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import Campaign, Character, Encounter, HealthTransaction
from hoard.campaigns.services.health import adjust_health, take_rest


class HealthServiceTests(TestCase):
    def setUp(self) -> None:
        campaign = Campaign.objects.create(name="Hoard")
        self.character = Character.objects.create(
            campaign=campaign,
            name="Hero",
            rolled_hit_points=20,
            current_hp=12,
            temporary_hp=5,
        )

    def test_damage_uses_temporary_hp_before_current_hp(self) -> None:
        updated = adjust_health(self.character, reason="damage", amount=8)

        self.assertEqual(updated.current_hp, 9)
        self.assertEqual(updated.temporary_hp, 0)
        posted = HealthTransaction.objects.get(character=self.character)
        self.assertEqual(posted.reason, HealthTransaction.Reason.DAMAGE)
        self.assertEqual((posted.current_hp_before, posted.current_hp_after), (12, 9))
        self.assertEqual(
            (posted.temporary_hp_before, posted.temporary_hp_after),
            (5, 0),
        )

    def test_healing_does_not_exceed_max_hp(self) -> None:
        updated = adjust_health(self.character, reason="healing", amount=50)

        self.assertEqual(updated.current_hp, 20)

    def test_short_rest_adds_regained_hp_and_clears_temporary_hp(self) -> None:
        updated = take_rest(self.character, kind="short", regained_hp=6)

        self.assertEqual(updated.current_hp, 18)
        self.assertEqual(updated.temporary_hp, 0)

    def test_long_rest_restores_max_hp_and_clears_temporary_hp(self) -> None:
        updated = take_rest(self.character, kind="long")

        self.assertEqual(updated.current_hp, 20)
        self.assertEqual(updated.temporary_hp, 0)

    def test_rests_are_rejected_during_combat(self) -> None:
        Encounter.objects.create(campaign=self.character.campaign)

        with self.assertRaisesMessage(
            ValidationError,
            "You cannot rest during combat.",
        ):
            take_rest(self.character, kind="short", regained_hp=6)
        with self.assertRaisesMessage(
            ValidationError,
            "You cannot rest during combat.",
        ):
            take_rest(self.character, kind="long")

        self.character.refresh_from_db()
        self.assertEqual(self.character.current_hp, 12)
        self.assertEqual(self.character.temporary_hp, 5)
