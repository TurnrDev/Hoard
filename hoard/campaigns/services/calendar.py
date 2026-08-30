"""Commands that change a campaign calendar."""

from __future__ import annotations

from hoard.campaigns.models import Campaign


class CampaignCalendarService:
    """Applies validated calendar changes to a campaign."""

    def adjust_day(self, campaign: Campaign, amount: int) -> None:
        campaign.adjust_calendar_day(amount)
        campaign.full_clean()
        campaign.save(update_fields=("calendar_year", "calendar_day"))
