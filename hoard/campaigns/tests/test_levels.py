from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from hoard.campaigns.consumers import ContextConsumer
from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
)
from hoard.campaigns.services import approve_campaign_level
from hoard.campaigns.services.native import native_class_details
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)


class CampaignLevelTests(TestCase):
    def setUp(self) -> None:
        self.campaign = Campaign.objects.create(
            name="Progression", shared_experience=300
        )
        self.gm_user = get_user_model().objects.create_user(username="gm")
        self.gm = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.gm_user,
            kind=CampaignContext.Kind.GM,
        )

    def test_gm_approval_is_immediate_and_blocks_until_active_players_finish(
        self,
    ) -> None:
        player = get_user_model().objects.create_user(username="active")
        context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=player,
            kind=CampaignContext.Kind.PC,
        )
        character = Character.objects.create(
            campaign=self.campaign,
            context=context,
            is_active=True,
            name="Active",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )
        repository = CompendiumRepository.objects.create(
            identifier="progression-test",
            name="Progression test",
        )
        source = CompendiumSource.objects.create(
            repository=repository,
            identifier="5e",
            name="5e",
            system_definition={"id": "5e", "character_stats": []},
        )
        fighter = CompendiumEntry.objects.create(
            source=source,
            kind=CompendiumEntry.Kind.CLASS,
            source_identifier="fighter",
            name="Fighter",
            data={
                "resource_id": "class",
                "stats": {"name": {"value": "Fighter"}},
            },
        )
        self.campaign.compendium_sources.add(source)
        character.native_system_source = source
        character.native_state = {
            "classes": [native_class_details(fighter, class_level=1)]
        }
        character.native_resources.add(fighter)
        character.save(update_fields=("native_system_source", "native_state"))

        event = approve_campaign_level(self.campaign, created_by=self.gm)

        self.campaign.refresh_from_db()
        self.assertEqual((event.previous_level, event.next_level), (1, 2))
        self.assertEqual(ContextConsumer._audit_data(event)["ledger_label"], "Level Up")
        self.assertEqual(self.campaign.level, 2)
        self.assertEqual(character.level, 1)
        self.assertLess(character.level, self.campaign.level)
        self.campaign.shared_experience = 900
        self.campaign.save(update_fields=("shared_experience",))
        with self.assertRaises(ValidationError):
            approve_campaign_level(self.campaign, created_by=self.gm)
