from uuid import uuid7

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TransactionTestCase, override_settings

from hoard.campaigns.consumers import UserConsumer
from hoard.campaigns.models import Campaign, CampaignContext, Character
from hoard.campaigns.services import create_invitation
from hoard.routing import websocket_urlpatterns


def request_id() -> str:
    """Return a fresh protocol-compliant request identifier for a test message."""
    return str(uuid7())


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

    async def context_request(self, message: dict):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/contexts/{self.context.pk}/"
        )
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
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
        message = {"type": "user.contexts.list", "request_id": request_id()}
        response = async_to_sync(self.user_request)(message)

        self.assertEqual(response["type"], "query.result")
        self.assertEqual([row["id"] for row in response["data"]], [self.context.pk])

    def test_campaign_query_returns_minimal_release_data(self) -> None:
        player_user = get_user_model().objects.create_user(username="player")
        player_context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=player_user,
            kind=CampaignContext.Kind.PC,
        )
        Character.objects.create(
            campaign=self.campaign,
            context=player_context,
            kind=Character.Kind.PC,
            is_active=True,
            name="Hero",
        )
        Character.objects.create(
            campaign=self.campaign,
            kind=Character.Kind.NPC,
            is_active=True,
            name="Guide",
        )
        message = {"type": "campaign.get", "request_id": request_id()}
        response = async_to_sync(self.context_request)(message)

        self.assertEqual(response["type"], "query.result")
        self.assertEqual(response["data"]["name"], "Socket campaign")
        self.assertEqual(
            {member["username"] for member in response["data"]["members"]},
            {"socket-user", "player"},
        )
        self.assertEqual(
            {character["name"] for character in response["data"]["characters"]},
            {"Guide", "Hero"},
        )
        player_data = next(
            character
            for character in response["data"]["characters"]
            if character["name"] == "Hero"
        )
        self.assertTrue(player_data["is_player_character"])
        self.assertTrue(player_data["is_active"])
        self.assertEqual(player_data["context_id"], player_context.pk)
        self.assertIn("portrait_url", player_data)
        self.assertIn("money", player_data)
        self.assertNotIn("encounter", response["data"])
        self.assertNotIn("incomplete_level_ups", response["data"])

    def test_context_socket_correlates_requests(self) -> None:
        message = {"type": "campaign.calendar.get", "request_id": request_id()}
        response = async_to_sync(self.context_request)(message)

        self.assertEqual(response["type"], "query.result")
        self.assertEqual(response["request_id"], message["request_id"])
        self.assertEqual(response["data"]["year"], 81)

    def test_invalid_request_identifier_is_rejected(self) -> None:
        message = {
            "type": "campaign.calendar.get",
            "request_id": "not-a-uuid7",
        }
        response = async_to_sync(self.context_request)(message)

        self.assertEqual(response["type"], "query.error")
        self.assertEqual(response["code"], "invalid_request_id")

    def test_removed_operation_is_unsupported(self) -> None:
        message = {
            "type": "campaign.encounter.start",
            "request_id": request_id(),
        }
        response = async_to_sync(self.context_request)(message)

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "unsupported_message")


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
        "local": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
)
class InviteSocketTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="invite-gm")
        self.campaign = Campaign.objects.create(name="Invite campaign")
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.GM,
        )

    async def invite_request(self, token: str, message: dict) -> dict:
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/invites/{token}/"
        )
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from(timeout=2)
        await communicator.disconnect()
        return response

    def test_anonymous_visitor_can_inspect_a_valid_invitation(self) -> None:
        _, token = create_invitation(self.context)
        message = {"type": "invite.inspect", "request_id": request_id()}

        response = async_to_sync(self.invite_request)(token, message)

        self.assertEqual(response["type"], "query.result")
        self.assertEqual(response["data"]["campaign_name"], "Invite campaign")
        self.assertFalse(response["data"]["authenticated"])

    def test_invalid_invitation_returns_a_structured_error(self) -> None:
        message = {"type": "invite.inspect", "request_id": request_id()}

        response = async_to_sync(self.invite_request)("missing-token", message)

        self.assertEqual(response["type"], "query.error")
        self.assertEqual(response["code"], "validation_error")
        self.assertEqual(response["detail"], ["Invitation not found."])
