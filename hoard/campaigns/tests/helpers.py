from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from hoard.campaigns.models import Campaign, CampaignContext, Character
from hoard.routing import websocket_urlpatterns


class ContextSocketMixin:
    async def _socket_request(self, user, context_id: int, message: dict):
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

    def socket_request(self, user, context_id: int, message_type: str, **payload):
        return async_to_sync(self._socket_request)(
            user,
            context_id,
            {"type": message_type, "request_id": "test-request", **payload},
        )


def make_character(
    campaign: Campaign,
    name: str = "Hero",
    *,
    active: bool = False,
    context: CampaignContext | bool = True,
) -> Character:
    membership = None
    if isinstance(context, CampaignContext):
        membership = context
    elif context:
        user = get_user_model().objects.create_user(
            username=f"{name}-{CampaignContext.objects.count()}"
        )
        membership = CampaignContext.objects.create(
            campaign=campaign, user=user, kind=CampaignContext.Kind.PC
        )
    return Character.objects.create(
        campaign=campaign,
        context=membership,
        name=name,
        race="Human",
        character_class="Fighter",
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
        is_active=active,
    )
