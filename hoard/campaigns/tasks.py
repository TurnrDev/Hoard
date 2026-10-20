"""Background refreshes for live DiceCloud campaign projections."""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from .models import Campaign
from .realtime import notify_campaign_changed
from .services.dicecloud import (
    DiceCloudError,
    cached_projection,
    clear_refresh_failure,
    projections_differ,
    record_refresh_failure,
    refresh_creature,
    refresh_is_allowed,
)

logger = logging.getLogger(__name__)

LIVE_SYNC_INTERVAL_SECONDS = 10
PRESENCE_WINDOW_SECONDS = 60
LIVE_SYNC_LOCK_KEY = "dicecloud:live-sync:lock"
LIVE_SYNC_LOCK_TIMEOUT_SECONDS = 120


@shared_task
def refresh_active_dicecloud_profiles() -> None:
    """Refresh active linked profiles for campaigns with a recently seen context."""
    if not cache.add(LIVE_SYNC_LOCK_KEY, "1", LIVE_SYNC_LOCK_TIMEOUT_SECONDS):
        return

    try:
        cutoff = timezone.now() - timedelta(seconds=PRESENCE_WINDOW_SECONDS)
        campaigns = Campaign.objects.filter(
            contexts__is_active=True,
            contexts__last_seen_at__gte=cutoff,
        ).distinct()

        for campaign in campaigns:
            profiles_changed = False
            characters = campaign.characters.filter(
                is_active=True,
            ).exclude(dicecloud_creature_id="")

            for character in characters:
                creature_id = character.dicecloud_creature_id
                if not refresh_is_allowed(creature_id):
                    continue

                previous = cached_projection(creature_id)
                try:
                    current = refresh_creature(creature_id)
                except DiceCloudError as error:
                    delay = record_refresh_failure(creature_id)
                    logger.warning(
                        "DiceCloud live sync failed for creature %s; retrying in %s seconds: %s",
                        creature_id,
                        delay,
                        error,
                    )
                    continue

                clear_refresh_failure(creature_id)
                if projections_differ(previous, current):
                    profiles_changed = True

            if profiles_changed:
                notify_campaign_changed(campaign.pk)
    finally:
        cache.delete(LIVE_SYNC_LOCK_KEY)
