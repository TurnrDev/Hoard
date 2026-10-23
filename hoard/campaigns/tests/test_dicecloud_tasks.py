from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from hoard.campaigns.models import Campaign, CampaignContext, Character
from hoard.campaigns.services.dicecloud import (
    DiceCloudUnavailable,
    projection_cache_key,
)
from hoard.campaigns.tasks import refresh_active_dicecloud_profiles


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class DiceCloudLiveSyncTaskTests(TestCase):
    creature_id = "sfdxGdwav3hoNATLJ"

    def setUp(self) -> None:
        cache.clear()
        self.campaign = Campaign.objects.create(name="Live DiceCloud campaign")
        self.user = get_user_model().objects.create_user(
            username="live-player", password="test-password"
        )
        self.context = CampaignContext.objects.create(
            campaign=self.campaign,
            user=self.user,
            kind=CampaignContext.Kind.PC,
        )
        self.character = Character.objects.create(
            campaign=self.campaign,
            context=self.context,
            dicecloud_creature_id=self.creature_id,
            is_active=True,
        )

    def profile(self, name: str = "Ama", fetched_at: str = "2026-10-20T12:00:00Z"):
        return {
            "id": self.creature_id,
            "name": name,
            "fetched_at": fetched_at,
            "stale": False,
            "stats": {"hitPoints": 31},
        }

    def make_campaign_present(self) -> None:
        self.context.last_seen_at = timezone.now()
        self.context.save(update_fields=("last_seen_at",))

    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_inactive_campaigns_do_not_fetch_profiles(self, refresh):
        refresh_active_dicecloud_profiles()

        refresh.assert_not_called()

    @patch("hoard.campaigns.tasks.notify_campaign_changed")
    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_refreshes_active_linked_profiles_for_present_campaigns(
        self, refresh, notify
    ):
        self.make_campaign_present()
        Character.objects.create(
            campaign=self.campaign,
            dicecloud_creature_id="inactiveDiceCloud01",
            is_active=False,
        )
        refresh.return_value = self.profile()

        refresh_active_dicecloud_profiles()

        refresh.assert_called_once_with(self.creature_id)
        notify.assert_called_once_with(self.campaign.pk)

    @patch("hoard.campaigns.tasks.notify_campaign_changed")
    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_unchanged_profiles_do_not_publish_a_campaign_event(self, refresh, notify):
        self.make_campaign_present()
        cached = self.profile(fetched_at="2026-10-20T11:59:50Z")
        cache.set(projection_cache_key(self.creature_id), cached, 60)
        refresh.return_value = self.profile(fetched_at="2026-10-20T12:00:00Z")

        refresh_active_dicecloud_profiles()

        refresh.assert_called_once_with(self.creature_id)
        notify.assert_not_called()

    @patch("hoard.campaigns.tasks.notify_campaign_changed")
    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_changed_profiles_publish_one_campaign_event(self, refresh, notify):
        self.make_campaign_present()
        cache.set(projection_cache_key(self.creature_id), self.profile(), 60)
        refresh.return_value = self.profile(name="Updated Ama")

        refresh_active_dicecloud_profiles()

        notify.assert_called_once_with(self.campaign.pk)

    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_failures_use_a_retry_cooldown(self, refresh):
        self.make_campaign_present()
        refresh.side_effect = DiceCloudUnavailable("offline")

        refresh_active_dicecloud_profiles()
        refresh_active_dicecloud_profiles()

        refresh.assert_called_once_with(self.creature_id)

    @patch("hoard.campaigns.tasks.refresh_creature")
    def test_presence_window_excludes_stale_contexts(self, refresh):
        self.context.last_seen_at = timezone.now() - timedelta(seconds=61)
        self.context.save(update_fields=("last_seen_at",))

        refresh_active_dicecloud_profiles()

        refresh.assert_not_called()
