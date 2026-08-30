"""Campaign-wide event contracts."""

from typing import Literal

from pydantic import BaseModel


class CampaignLevelChangedEvent(BaseModel):
    """Authoritative campaign level after a GM approves a level-up."""

    type: Literal["campaign.level_changed"] = "campaign.level_changed"
    previous_level: int
    next_level: int
    request_id: str | None = None


class CampaignStateChangedEvent(BaseModel):
    """Compatibility notification for a changed campaign render model."""

    type: Literal["campaign.state_changed"] = "campaign.state_changed"
    request_id: str | None = None
