from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    HealthTransaction,
)
from hoard.campaigns.services import post_health_transaction
from hoard.compendium.models import CompendiumRepository, CompendiumSource


class DateAndHealthTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(
            name="Dated campaign",
            calendar_era_abbreviation="PD",
            calendar_year=81,
            calendar_day=11,
            level=3,
        )
        self.user = get_user_model().objects.create_user(username="player")
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.PC,
        )
        repository = CompendiumRepository.objects.get_or_create(
            identifier="default",
            defaults={"name": "Default systems"},
        )[0]
        source = CompendiumSource.objects.update_or_create(
            repository=repository,
            identifier="5e",
            defaults={
                "name": "5e",
                "system_definition": {
                    "id": "5e",
                    "character_stats": [
                        {
                            "id": "current_hp",
                            "type": "base",
                            "default_value": 1,
                        },
                        {
                            "id": "base_hp",
                            "type": "base",
                            "default_value": 1,
                        },
                        *[
                            {
                                "id": f"death_saving_throws_{kind}_{index}",
                                "type": "base",
                                "default_value": False,
                            }
                            for kind in ("success", "failure")
                            for index in range(1, 4)
                        ],
                    ],
                },
            },
        )[0]
        self.campaign.native_system_source = source
        self.campaign.save(update_fields=("native_system_source",))
        self.campaign.compendium_sources.add(source)
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.context,
            is_active=True,
            name="Hero",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            base_hp=20,
            hp_adjustment=2,
            current_hp=10,
            temporary_hp=3,
            native_system_source=source,
        )

    def test_hp_uses_base_ability_per_level_and_hp_only_adjustment(self) -> None:
        self.assertEqual(self.character.max_hp, 28)

    def test_health_transaction_snapshots_both_dates_and_balances(self) -> None:
        posted = post_health_transaction(
            self.character,
            reason=HealthTransaction.Reason.DAMAGE,
            current_hp_delta=-4,
            description="Trap",
            created_by=self.context,
        )
        self.campaign.calendar_day = 12
        self.campaign.save(update_fields=("calendar_day",))

        self.character.refresh_from_db()
        self.assertEqual(
            (self.character.current_hp, self.character.temporary_hp), (9, 0)
        )
        self.assertEqual((posted.current_hp_delta, posted.temporary_hp_delta), (-1, -3))
        self.assertEqual(posted.campaign_date, "PD 81, 11th")
        self.assertIsNotNone(posted.occurred_at.tzinfo)
        with self.assertRaises(ValidationError):
            posted.delete()

    def test_healing_above_zero_resets_death_saving_throws(self) -> None:
        death_saves = {
            f"death_saving_throws_{kind}_{index}": True
            for kind in ("success", "failure")
            for index in range(1, 4)
        }
        self.character.current_hp = 0
        self.character.temporary_hp = 0
        self.character.is_dead = True
        self.character.native_state = {
            "current_hp": 0,
            "hoard_temporary_hp": 0,
            "hoard_is_dead": True,
            **death_saves,
        }
        self.character.save(
            update_fields=(
                "current_hp",
                "temporary_hp",
                "is_dead",
                "native_state",
            )
        )

        post_health_transaction(
            self.character,
            reason=HealthTransaction.Reason.HEALING,
            current_hp_delta=1,
            created_by=self.context,
        )

        self.character.refresh_from_db()
        self.assertEqual(self.character.current_hp, 1)
        self.assertFalse(self.character.is_dead)
        self.assertFalse(
            any(self.character.native_state[stat] for stat in death_saves)
        )
