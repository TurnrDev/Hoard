import time
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from hoard.campaigns.consumers import ContextConsumer, UserConsumer
from hoard.campaigns.models import (
    Campaign,
    CampaignContext,
    Character,
    CharacterClassLevel,
    CharacterLevelProgress,
)
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)
from hoard.routing import websocket_urlpatterns


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
        "local": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
)
class ContextSocketTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="socket-user")
        self.campaign = Campaign.objects.create(name="Socket campaign")
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.GM,
        )

    async def socket_request(self, user, context_id: int, message: dict):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/contexts/{context_id}/"
        )
        communicator.scope["user"] = user
        connected, code = await communicator.connect()
        if not connected:
            return {"type": "connection.error", "code": code}
        await communicator.send_json_to(message)
        while True:
            response = await communicator.receive_json_from(timeout=2)
            if response.get("request_id") == message.get("request_id"):
                break
        await communicator.disconnect()
        return response

    async def user_request(self, message: dict):
        communicator = WebsocketCommunicator(UserConsumer.as_asgi(), "/ws/user/")
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from(timeout=2)
        await communicator.disconnect()
        return response

    def test_user_socket_lists_exact_acting_contexts(self) -> None:
        response = async_to_sync(self.user_request)(
            {"type": "user.contexts.list", "request_id": "contexts-1"}
        )

        self.assertEqual(response["request_id"], "contexts-1")
        self.assertEqual([row["id"] for row in response["data"]], [self.context.pk])

    def test_context_socket_correlates_requests(self) -> None:
        response = async_to_sync(self.socket_request)(
            self.user,
            self.context.pk,
            {"type": "campaign.calendar.get", "request_id": "calendar-1"},
        )

        self.assertEqual(response["type"], "response")
        self.assertEqual(response["request_id"], "calendar-1")
        self.assertEqual(response["data"]["year"], 81)

    async def concurrent_requests(self):
        async def slow_definition(consumer, content):
            await database_sync_to_async(time.sleep)(0.25)
            return {"slow": True}

        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/contexts/{self.context.pk}/"
        )
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        with patch.object(ContextConsumer, "_builder_definition", slow_definition):
            await communicator.send_json_to(
                {
                    "type": "characters.builder.definition",
                    "request_id": "slow-definition",
                }
            )
            await communicator.send_json_to(
                {"type": "campaign.calendar.get", "request_id": "quick-calendar"}
            )
            first = await communicator.receive_json_from(timeout=1)
            second = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return first, second

    def test_slow_request_does_not_block_later_correlated_request(self) -> None:
        first, second = async_to_sync(self.concurrent_requests)()

        self.assertEqual(first["request_id"], "quick-calendar")
        self.assertEqual(second["request_id"], "slow-definition")

    def test_campaign_response_serializes_archived_character_datetimes(self) -> None:
        Character.objects.create(
            campaign=self.campaign,
            name="Archived",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            is_archived=True,
            archived_at=timezone.now(),
        )

        response = async_to_sync(self.socket_request)(
            self.user,
            self.context.pk,
            {"type": "campaign.get", "request_id": "archived-1"},
        )

        self.assertEqual(response["type"], "response")
        self.assertIsInstance(response["data"]["characters"][0]["archived_at"], str)

    def test_context_socket_rejects_a_different_user(self) -> None:
        stranger = get_user_model().objects.create_user(username="stranger")

        response = async_to_sync(self.socket_request)(
            stranger,
            self.context.pk,
            {"type": "campaign.get", "request_id": "forbidden-1"},
        )

        self.assertEqual(response, {"type": "connection.error", "code": 4403})

    def test_player_can_save_and_complete_an_overridden_draft(self) -> None:
        player = get_user_model().objects.create_user(username="builder")
        context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=player,
            kind=CampaignContext.Kind.PC,
        )
        character = Character.objects.create(
            campaign=self.campaign,
            context=context,
            name="Builder",
            race="",
            character_class="",
            strength=10,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            base_hp=10,
            is_active=False,
            is_build_complete=False,
        )
        saved = async_to_sync(self.socket_request)(
            player,
            context.pk,
            {
                "type": "characters.builder.save",
                "request_id": "builder-save",
                "character_id": character.pk,
                "fields": {"name": "Builder", "race": "Custom lineage"},
                "class_levels": [
                    {
                        "level": 1,
                        "class_name": "Fighter",
                        "is_override": True,
                    }
                ],
                "is_override": True,
            },
        )
        completed = async_to_sync(self.socket_request)(
            player,
            context.pk,
            {
                "type": "characters.builder.complete",
                "request_id": "builder-complete",
                "character_id": character.pk,
            },
        )

        self.assertEqual(saved["type"], "response")
        self.assertEqual(completed["type"], "response")
        character.refresh_from_db()
        self.assertTrue(character.is_active)
        self.assertTrue(character.is_build_complete)
        self.assertEqual(character.current_hp, character.max_hp)

    def test_player_completes_only_the_pending_level_up(self) -> None:
        player = get_user_model().objects.create_user(username="leveler")
        context = CampaignContext.objects.create(
            campaign=self.campaign, user=player, kind=CampaignContext.Kind.PC
        )
        self.campaign.level = 2
        self.campaign.save(update_fields=("level",))
        character = Character.objects.create(
            campaign=self.campaign,
            context=context,
            name="Leveler",
            race="Human",
            character_class="Fighter 1",
            strength=10,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            base_hp=10,
            current_hp=10,
            is_active=True,
            is_build_complete=True,
        )
        CharacterClassLevel.objects.create(
            character=character, level=1, class_name="Fighter"
        )
        CharacterLevelProgress.objects.create(
            character=character, level=1, is_complete=True
        )
        CharacterLevelProgress.objects.create(
            character=character, level=2, is_complete=False
        )
        repository = CompendiumRepository.objects.create(
            identifier="level-test", name="Level test"
        )
        source = CompendiumSource.objects.create(
            repository=repository, identifier="5e", name="5e"
        )
        self.campaign.compendium_sources.add(source)
        fighter = CompendiumEntry.objects.create(
            source=source,
            kind=CompendiumEntry.Kind.CLASS,
            source_identifier="fighter",
            name="Fighter",
            source_book="PHB",
            data={"hitDie": "d10"},
        )

        definition = async_to_sync(self.socket_request)(
            player,
            context.pk,
            {
                "type": "characters.level_up.definition",
                "request_id": "level-definition",
                "character_id": character.pk,
            },
        )
        completed = async_to_sync(self.socket_request)(
            player,
            context.pk,
            {
                "type": "characters.level_up.complete",
                "request_id": "level-complete",
                "character_id": character.pk,
                "class_entry_id": fighter.pk,
                "hp_method": "average",
                "hp_increase": 6,
                "ability_adjustments": {},
                "asi_choice": "",
                "choices": [],
            },
        )

        self.assertEqual(definition["type"], "response")
        self.assertEqual(definition["data"]["level"], 2)
        self.assertEqual(completed["type"], "response")
        character.refresh_from_db()
        self.assertEqual(character.base_hp, 16)
        self.assertEqual(character.current_hp, 16)
        self.assertEqual(character.ability_score_adjustments, {})
        self.assertTrue(character.level_progress.get(level=2).is_complete)
        self.assertEqual(character.class_levels.count(), 2)
