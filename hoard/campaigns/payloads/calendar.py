"""Calendar query, command, and event contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..models import Campaign


class CampaignCalendarData(BaseModel):
    """The current calendar fields required by application clients."""

    era_abbreviation: str
    era_name: str
    year: int
    day: int

    @classmethod
    def from_campaign(cls, campaign: Campaign) -> CampaignCalendarData:
        """Build the transport contract from the authoritative campaign model."""
        return cls(
            era_abbreviation=campaign.calendar_era_abbreviation,
            era_name=campaign.calendar_era_name,
            year=campaign.calendar_year,
            day=campaign.calendar_day,
        )


class CalendarAdjustmentCommand(BaseModel):
    """Validated input for moving the campaign calendar by one day."""

    amount: Literal[-1, 1]


class CampaignCalendarChangedEvent(BaseModel):
    """Authoritative calendar state published after a calendar command."""

    type: Literal["campaign.calendar_changed"] = "campaign.calendar_changed"
    calendar: CampaignCalendarData
    request_id: str | None = None
