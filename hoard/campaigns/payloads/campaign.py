"""Campaign-wide event contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class ExperienceRecipientCountCommand(BaseModel):
    """Validated input for the campaign-wide XP divisor."""

    experience_recipient_count: int = Field(gt=0, le=100)


class CampaignStateChangedEvent(BaseModel):
    """Compatibility notification for a changed campaign render model."""

    type: Literal["campaign.state_changed"] = "campaign.state_changed"
    request_id: str | None = None
