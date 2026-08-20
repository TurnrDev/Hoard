from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


def campaign_group_name(campaign_id: int) -> str:
    return f"campaign-{campaign_id}"


def notify_campaign_changed(campaign_id: int) -> None:
    """Notify connected campaign members after a successful DB commit."""

    def send() -> None:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                campaign_group_name(campaign_id), {"type": "campaign.changed"}
            )

    transaction.on_commit(send)
