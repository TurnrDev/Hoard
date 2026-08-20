from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import CampaignContext
from .realtime import campaign_group_name


class CampaignConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope["user"]
        campaign_id = int(self.scope["url_route"]["kwargs"]["campaign_id"])
        if not user.is_authenticated or not await self._has_active_context(user.pk, campaign_id):
            await self.close(code=4403)
            return
        self.group_name = campaign_group_name(campaign_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def campaign_changed(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "campaign.changed"})

    @database_sync_to_async
    def _has_active_context(self, user_id: int, campaign_id: int) -> bool:
        return CampaignContext.objects.filter(
            user_id=user_id, campaign_id=campaign_id, is_active=True
        ).exists()
