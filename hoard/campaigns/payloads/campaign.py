"""Campaign-wide event contracts."""

from typing import Literal

from pydantic import BaseModel


class CampaignStateChangedEvent(BaseModel):
    """Compatibility notification for a changed campaign render model."""

    type: Literal["campaign.state_changed"] = "campaign.state_changed"
    request_id: str | None = None
