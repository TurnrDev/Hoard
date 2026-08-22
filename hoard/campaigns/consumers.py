from __future__ import annotations

import logging
import secrets

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Q
from ninja.errors import HttpError

from hoard.compendium.ingest.repository import SUPPORTED_SOURCE_IDENTIFIERS
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)
from hoard.compendium.tasks import import_campaign_repository

from .models import CampaignContext
from .realtime import campaign_group_name, notify_campaign_changed

logger = logging.getLogger(__name__)


class CampaignConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope["user"]
        campaign_id = int(self.scope["url_route"]["kwargs"]["campaign_id"])
        if not user.is_authenticated or not await self._has_active_context(
            user.pk, campaign_id
        ):
            await self.close(code=4403)
            return
        self.campaign_id = campaign_id
        self.group_name = campaign_group_name(campaign_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, object], **kwargs: object) -> None:
        message_type = content.get("type")
        if not isinstance(message_type, str):
            await self.send_json(
                {"type": "error", "detail": "A message type is required."}
            )
            return
        handlers = {
            "compendium.items.list": self._item_list,
            "compendium.items.create": self._item_create,
            "compendium.items.update": self._item_update,
            "compendium.items.delete": self._item_delete,
            "compendium.search": self._compendium_search,
            "compendium.sources.list": self._source_list,
            "compendium.sources.enable": self._source_enable,
            "compendium.sources.disable": self._source_disable,
            "compendium.repositories.list": self._repository_list,
        }
        handler = handlers.get(message_type)
        if handler is not None:
            await self._request_response(content, handler)
            return
        if message_type != "compendium.repositories.import":
            await self.send_json({"type": "error", "detail": "Unsupported message."})
            return
        repository_id = content.get("repository_id")
        ref = content.get("ref", "")
        if not (
            isinstance(repository_id, str)
            and repository_id.strip()
            and isinstance(ref, str)
        ):
            await self.send_json(
                {
                    "type": "repository.import.error",
                    "detail": "A registered repository is required.",
                }
            )
            return
        job_id = secrets.token_urlsafe(8)
        try:
            queued = await self._enqueue_import(job_id, repository_id.strip(), ref)
        except Exception:
            logger.exception("Unable to queue Compendium repository import.")
            await self.send_json(
                {
                    "type": "repository.import.error",
                    "detail": "Unable to queue the repository import.",
                }
            )
            return
        if not queued:
            await self.send_json(
                {
                    "type": "repository.import.error",
                    "detail": "A repository import is already running.",
                }
            )
            return
        await self.send_json({"type": "repository.import.started", "job_id": job_id})

    async def campaign_changed(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "campaign.changed"})

    async def repository_import_progress(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.progress", **event})

    async def repository_import_finished(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.finished", **event})

    async def repository_import_error(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.error", **event})

    async def _request_response(self, content: dict[str, object], handler) -> None:
        request_id = content.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            await self.send_json(
                {"type": "response.error", "detail": "A request ID is required."}
            )
            return
        try:
            data = await handler(content)
        except (HttpError, PermissionError, ValueError, ValidationError) as error:
            detail = getattr(error, "message", None) or str(error)
            await self.send_json(
                {
                    "type": "response.error",
                    "request_id": request_id,
                    "detail": detail,
                }
            )
            return
        except Exception:
            logger.exception(
                "Unable to process Compendium request %s.", content.get("type")
            )
            await self.send_json(
                {
                    "type": "response.error",
                    "request_id": request_id,
                    "detail": "Unable to process the Compendium request.",
                }
            )
            return
        await self.send_json(
            {"type": "response", "request_id": request_id, "data": data}
        )

    @database_sync_to_async
    def _has_active_context(self, user_id: int, campaign_id: int) -> bool:
        return CampaignContext.objects.filter(
            user_id=user_id, campaign_id=campaign_id, is_active=True
        ).exists()

    @database_sync_to_async
    def _item_list(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _item_data, _items

        context = self._context()
        offset = self._nonnegative_integer(content, "offset")
        limit = min(self._positive_integer(content, "limit", default=100), 100)
        rows = list(
            _items(context.campaign).order_by("name")[offset : offset + limit + 1]
        )
        more = len(rows) > limit
        return {
            "items": [_item_data(item) for item in rows[:limit]],
            "next_offset": offset + limit if more else None,
        }

    @database_sync_to_async
    def _item_create(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _custom_source, _item_data

        context = self._context()
        name = self._string(content, "name", required=True, maximum=200)
        description = self._string(content, "description")
        item = CompendiumEntry(
            source=_custom_source(context.campaign),
            kind=CompendiumEntry.Kind.ITEM,
            source_identifier=f"custom:{name.lower()}",
            name=name,
            description=description,
            created_by=context,
        )
        item.full_clean()
        item.save()
        notify_campaign_changed(context.campaign_id)
        return _item_data(item)

    @database_sync_to_async
    def _item_update(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _editable_item, _item_data

        context = self._context()
        item = _editable_item(context, self._integer(content, "item_id"))
        if "name" in content:
            item.name = self._string(content, "name", required=True, maximum=200)
        if "description" in content:
            item.description = self._string(content, "description")
        item.full_clean()
        item.save()
        notify_campaign_changed(context.campaign_id)
        return _item_data(item)

    @database_sync_to_async
    def _item_delete(self, content: dict[str, object]) -> None:
        from .api import _editable_item

        context = self._context()
        item = _editable_item(context, self._integer(content, "item_id"))
        if item.inventory_entries.exists():
            raise HttpError(
                409, "Items referenced by ledger entries cannot be deleted."
            )
        item.delete()
        notify_campaign_changed(context.campaign_id)

    @database_sync_to_async
    def _compendium_search(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import _available_entries

        context = self._context()
        kind = self._string(content, "kind", required=True)
        query = self._string(content, "query")
        entries = _available_entries(context.campaign, kind)
        if query:
            entries = entries.filter(name__icontains=query)
        return [
            {
                "id": entry.pk,
                "name": entry.name,
                "description": entry.description,
                "kind": entry.kind,
                "source": entry.source.name,
            }
            for entry in entries.order_by("name")[:100]
        ]

    @database_sync_to_async
    def _source_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import _source_data

        context = self._context()
        enabled = set(context.campaign.compendium_sources.values_list("pk", flat=True))
        sources = CompendiumSource.objects.filter(
            Q(repository__campaign__isnull=True)
            | Q(repository__campaign=context.campaign)
        ).select_related("repository")
        return [_source_data(source, source.pk in enabled) for source in sources]

    @database_sync_to_async
    def _source_enable(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _gm, _source_data

        context = self._context()
        _gm(context)
        source = (
            CompendiumSource.objects.filter(
                Q(repository__campaign__isnull=True)
                | Q(repository__campaign=context.campaign),
                pk=self._integer(content, "source_id"),
            )
            .select_related("repository")
            .first()
        )
        if source is None:
            raise HttpError(404, "Compendium source not found.")
        context.campaign.compendium_sources.add(source)
        notify_campaign_changed(context.campaign_id)
        return _source_data(source, True)

    @database_sync_to_async
    def _source_disable(self, content: dict[str, object]) -> None:
        from .api import _gm

        context = self._context()
        _gm(context)
        source = context.campaign.compendium_sources.filter(
            pk=self._integer(content, "source_id")
        ).first()
        if source is None:
            raise HttpError(404, "Compendium source not found.")
        context.campaign.compendium_sources.remove(source)
        notify_campaign_changed(context.campaign_id)

    @database_sync_to_async
    def _repository_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        self._context()
        installed = set(
            CompendiumRepository.objects.filter(sources__isnull=False).values_list(
                "identifier", flat=True
            )
        )
        return [
            {
                "id": repository.identifier,
                "name": repository.name,
                "description": repository.description,
                "tags": repository.tags,
                "repository_url": repository.repository_url,
                "github_repository": repository.github_repository,
                "installed": repository.identifier in installed,
            }
            for repository in CompendiumRepository.objects.filter(campaign__isnull=True)
            if SUPPORTED_SOURCE_IDENTIFIERS.intersection(repository.tags)
        ]

    def _context(self) -> CampaignContext:
        context = (
            CampaignContext.objects.select_related("campaign", "user")
            .filter(
                campaign_id=self.campaign_id,
                user_id=self.scope["user"].pk,
                is_active=True,
            )
            .first()
        )
        if context is None:
            raise PermissionError("No active campaign context.")
        return context

    @staticmethod
    def _string(
        content: dict[str, object],
        key: str,
        *,
        required: bool = False,
        maximum: int | None = None,
    ) -> str:
        value = content.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be text.")
        value = value.strip()
        if required and not value:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")
        if maximum is not None and len(value) > maximum:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} is too long.")
        return value

    @staticmethod
    def _integer(content: dict[str, object], key: str) -> int:
        value = content.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")
        return value

    @staticmethod
    def _nonnegative_integer(content: dict[str, object], key: str) -> int:
        value = content.get(key, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                f"{key.replace('_', ' ').capitalize()} must be non-negative."
            )
        return value

    @staticmethod
    def _positive_integer(content: dict[str, object], key: str, *, default: int) -> int:
        value = content.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be positive.")
        return value

    @database_sync_to_async
    def _enqueue_import(self, job_id: str, repository_id: str, ref: str) -> bool:
        context = self._context()
        from .api import _gm

        _gm(context)
        repository = CompendiumRepository.objects.filter(
            identifier=repository_id, campaign__isnull=True
        ).first()
        if repository is None or not SUPPORTED_SOURCE_IDENTIFIERS.intersection(
            repository.tags
        ):
            raise HttpError(404, "Registered Compendium repository not found.")
        lock = f"compendium-repository-import:{self.campaign_id}"
        if not cache.add(lock, job_id, timeout=60 * 60):
            return False
        try:
            import_campaign_repository.apply_async(
                args=(self.campaign_id, job_id, repository_id, ref), task_id=job_id
            )
        except Exception:
            cache.delete(lock)
            raise
        return True
