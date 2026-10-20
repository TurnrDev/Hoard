from django.db import models
from django.utils import timezone


class PartyExperienceAward(models.Model):
    """Audit record for an award added to the campaign-wide XP total."""

    campaign = models.ForeignKey(
        "campaigns.Campaign", on_delete=models.CASCADE, related_name="party_xp_awards"
    )
    amount = models.IntegerField()
    recipient_count = models.PositiveIntegerField()
    awarded_per_player = models.IntegerField()
    discarded_amount = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=20, default="award")
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "campaigns.CampaignContext",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="party_xp_awards",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    campaign_era_abbreviation = models.CharField(max_length=20, null=True, blank=True)
    campaign_year = models.PositiveIntegerField(null=True, blank=True)
    campaign_day = models.PositiveSmallIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-occurred_at", "-pk")

    @property
    def campaign_date(self) -> str | None:
        if (
            self.campaign_era_abbreviation is None
            or self.campaign_year is None
            or self.campaign_day is None
        ):
            return None
        from .audit import format_campaign_date

        return format_campaign_date(
            self.campaign_era_abbreviation,
            self.campaign_year,
            self.campaign_day,
        )
