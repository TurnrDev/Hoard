from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def ordinal(value: int) -> str:
    """Return an English ordinal, including the 11th-13th exception."""
    suffix = (
        "th"
        if 10 < value % 100 < 14
        else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    )
    return f"{value}{suffix}"


def format_campaign_date(era: str, year: int, day: int) -> str:
    return f"{era} {year}, {ordinal(day)}"


class CampaignDatedEvent(models.Model):
    """Immutable event metadata shared by every campaign history stream."""

    campaign_id: int
    created_by_id: int | None

    campaign = models.ForeignKey(
        "campaigns.Campaign", verbose_name="Campaign", on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        "campaigns.CampaignContext", null=True, blank=True, on_delete=models.SET_NULL
    )
    occurred_at = models.DateTimeField(
        "Occurred At", default=timezone.now, editable=False
    )
    actor_username = models.CharField("Actor Username", max_length=150, blank=True)
    campaign_era_abbreviation = models.CharField(
        "Campaign Era Abbreviation", max_length=20, null=True, blank=True
    )
    campaign_year = models.PositiveIntegerField("Campaign Year", null=True, blank=True)
    campaign_day = models.PositiveSmallIntegerField(
        "Campaign Day", null=True, blank=True
    )

    class Meta:
        abstract = True

    @property
    def campaign_date(self) -> str | None:
        if (
            self.campaign_era_abbreviation is None
            or self.campaign_year is None
            or self.campaign_day is None
        ):
            return None
        return format_campaign_date(
            self.campaign_era_abbreviation, self.campaign_year, self.campaign_day
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            update_fields = set(kwargs.get("update_fields") or ())
            previous = (
                type(self).objects.filter(pk=self.pk).values("created_by_id").first()
            )
            if not (
                update_fields == {"created_by"}
                and previous
                and previous["created_by_id"] is None
                and self.created_by_id is not None
            ):
                raise ValidationError("Posted campaign events are immutable.")
            self.actor_username = self.created_by.user.get_username()
            kwargs["update_fields"] = ("created_by", "actor_username")
            return super().save(*args, **kwargs)
        if self.campaign_era_abbreviation is None:
            campaign = self.campaign
            self.campaign_era_abbreviation = campaign.calendar_era_abbreviation
            self.campaign_year = campaign.calendar_year
            self.campaign_day = campaign.calendar_day
        if not self.actor_username:
            self.actor_username = (
                self.created_by.user.get_username() if self.created_by_id else "System"
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError("Posted campaign events are immutable.")
