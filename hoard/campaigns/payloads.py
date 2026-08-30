"""Pydantic contracts shared by WebSocket and REST compatibility transports."""

from __future__ import annotations

from pydantic import BaseModel

from .models import Campaign


class CampaignCalendarData(BaseModel):
    """The current calendar fields required by application clients."""

    era_abbreviation: str
    era_name: str
    year: int
    day: int

    @classmethod
    def from_campaign(cls, campaign: Campaign) -> CampaignCalendarData:
        return cls(
            era_abbreviation=campaign.calendar_era_abbreviation,
            era_name=campaign.calendar_era_name,
            year=campaign.calendar_year,
            day=campaign.calendar_day,
        )
