from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from pydantic import BaseModel


def campaign_group_name(campaign_id: int) -> str:
    return f"campaign-{campaign_id}"


def notify_campaign_event(campaign_id: int, event: BaseModel) -> None:
    """Publish a JSON-ready domain event after a successful DB commit."""

    payload = event.model_dump(mode="json")

    def send() -> None:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                campaign_group_name(campaign_id),
                {"type": "domain.event", "event": payload},
            )

    transaction.on_commit(send)


def notify_campaign_changed(campaign_id: int, request_id: str | None = None) -> None:
    """Publish the temporary campaign-wide state-changed compatibility event."""
    from .payloads import CampaignStateChangedEvent

    notify_campaign_event(
        campaign_id,
        CampaignStateChangedEvent(request_id=request_id),
    )
