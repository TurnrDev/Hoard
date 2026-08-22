"""Background Compendium import jobs."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.core.exceptions import ValidationError

from hoard.campaigns.models import Campaign
from hoard.campaigns.realtime import campaign_group_name, notify_campaign_changed
from hoard.compendium.ingest.repository import import_repository
from hoard.compendium.models import CompendiumRepository

logger = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 2
PROGRESS_THROTTLE_SECONDS = 0.25


@dataclass
class ImportProgress:
    """Publish importer progress and a heartbeat on the campaign channel."""

    campaign_id: int
    job_id: str
    heartbeat_seconds: float = HEARTBEAT_SECONDS
    _stop: Event = field(default_factory=Event, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    _stage: str = field(default="queued", init=False)
    _message: str = field(default="Waiting for import worker", init=False)
    _current: int | None = field(default=None, init=False)
    _total: int | None = field(default=None, init=False)
    _last_published: float = field(default=0, init=False)
    _thread: Thread | None = field(default=None, init=False)

    def start(self) -> None:
        self._thread = Thread(target=self._publish_heartbeats, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def report(
        self, stage: str, message: str, current: int | None, total: int | None
    ) -> None:
        with self._lock:
            stage_changed = stage != self._stage
            self._stage = stage
            self._message = message
            self._current = current
            self._total = total
            now = time.monotonic()
            if (
                not stage_changed
                and now - self._last_published < PROGRESS_THROTTLE_SECONDS
            ):
                return
            self._last_published = now
            payload = self._payload()
        _broadcast(self.campaign_id, "repository.import.progress", **payload)

    def _publish_heartbeats(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            with self._lock:
                self._last_published = time.monotonic()
                payload = self._payload()
            _broadcast(
                self.campaign_id,
                "repository.import.progress",
                heartbeat=True,
                **payload,
            )

    def _payload(self) -> dict[str, str | int | None]:
        return {
            "job_id": self.job_id,
            "stage": self._stage,
            "message": self._message,
            "current": self._current,
            "total": self._total,
        }


@shared_task
def import_campaign_repository(
    campaign_id: int, job_id: str, repository_id: str, ref: str
) -> dict[str, int]:
    """Import a registered repository and enable its sources for a campaign."""
    progress = ImportProgress(campaign_id, job_id)
    progress.start()
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        repository = CompendiumRepository.objects.get(
            identifier=repository_id, campaign__isnull=True
        )
        created, updated, skipped = import_repository(
            repository,
            ref=ref,
            progress=progress.report,
        )
        campaign.compendium_sources.add(*repository.sources.all())
        notify_campaign_changed(campaign_id)
        result = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }
        _broadcast(
            campaign_id,
            "repository.import.finished",
            job_id=job_id,
            **result,
        )
        return result
    except ValidationError as error:
        _broadcast(
            campaign_id,
            "repository.import.error",
            job_id=job_id,
            detail=error.messages[0],
        )
        raise
    except Exception:
        logger.exception("Repository import failed unexpectedly.")
        _broadcast(
            campaign_id,
            "repository.import.error",
            job_id=job_id,
            detail="Repository import failed unexpectedly.",
        )
        raise
    finally:
        progress.stop()
        cache.delete(f"compendium-repository-import:{campaign_id}")


def _broadcast(campaign_id: int, event_type: str, **data: object) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            campaign_group_name(campaign_id), {"type": event_type, **data}
        )
