from __future__ import annotations

import asyncio
import json
import logging
import secrets
from datetime import timedelta

from asgiref.sync import ThreadSensitiveContext
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from ninja.errors import HttpError

from hoard.compendium.ingest.repository import SUPPORTED_SOURCE_IDENTIFIERS
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)
from hoard.compendium.tasks import import_campaign_repository

from .models import (
    CampaignContext,
    CampaignInvitation,
    CampaignLevelEvent,
    Character,
    CharacterChoice,
    CharacterClassLevel,
    CharacterHistory,
    CharacterLevelProgress,
    HealthTransaction,
    InvitationEvent,
    MembershipEvent,
)
from .payloads import (
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
    CampaignInvitationChangedEvent,
    CampaignInvitationData,
    CampaignLevelChangedEvent,
    CampaignMemberData,
    CampaignMembershipChangedEvent,
    CharacterHealthChangedEvent,
    CharacterLifecycleData,
    CharacterLifecycleEvent,
)
from .protocol import (
    CommandAcknowledgementEnvelope,
    QueryResultEnvelope,
    RequestEnvelope,
    RequestErrorEnvelope,
    error_type,
    is_uuid7,
    operation_definition,
    operation_kind,
    result_type,
)
from .realtime import (
    campaign_group_name,
    notify_campaign_changed,
    notify_campaign_event,
)
from .services import (
    CharacterHealthService,
    CharacterLifecycleService,
    accept_invitation,
    approve_campaign_level,
    create_invitation,
    post_health_transaction,
    register_and_accept,
)
from .services.calendar import CampaignCalendarService
from .services.history import character_snapshot, record_character_history

logger = logging.getLogger(__name__)
MAX_WEBSOCKET_RESPONSE_BYTES = settings.DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE - 65_536


def _unwrapped(value: object) -> object:
    while isinstance(value, dict) and "value" in value:
        value = value["value"]
    return value


def _choice_labels(value: object) -> list[str]:
    """Extract compact labels from legacy and normalized rule payloads."""
    value = _unwrapped(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [label for row in value for label in _choice_labels(row)]
    if not isinstance(value, dict):
        return []
    stats = _unwrapped(value.get("stats"))
    if isinstance(stats, dict):
        name = _unwrapped(stats.get("name"))
        if isinstance(name, str) and name.strip():
            return [name.strip()]
        for key in ("options", "item"):
            if key in stats:
                labels = _choice_labels(stats[key])
                if labels:
                    return labels
    name = _unwrapped(value.get("name"))
    if isinstance(name, str) and name.strip():
        return [name.strip()]
    for key in ("options", "item"):
        if key in value:
            labels = _choice_labels(value[key])
            if labels:
                return labels
    return []


def _class_subclasses(
    sources: tuple[dict[str, object], dict[str, object]], default_source: str
) -> tuple[int, list[dict[str, object]]]:
    """Return compact subclass metadata without returning the full class payload."""
    selection_level: object = None
    subclass_rows: object = None
    for source in sources:
        selection_level = selection_level or _unwrapped(
            source.get("archetype_selection_level")
            or source.get("subclass_selection_level")
        )
        subclass_rows = subclass_rows or _unwrapped(
            source.get("archetypes")
            or source.get("subclasses")
            or source.get("csubclasses")
        )
    # RPG Companion omits the field for classes whose subclass choice uses its
    # normal default of class level 3. Classes that differ carry an explicit value.
    try:
        unlock_level = int(selection_level) if selection_level is not None else 3
    except TypeError, ValueError:
        unlock_level = 3
    unlock_level = min(20, max(1, unlock_level))

    subclasses: list[dict[str, object]] = []
    if not isinstance(subclass_rows, list):
        return unlock_level, subclasses
    for row in subclass_rows:
        row = _unwrapped(row)
        if not isinstance(row, dict):
            continue
        stats = _unwrapped(row.get("stats"))
        stats = stats if isinstance(stats, dict) else row
        name = _unwrapped(stats.get("name"))
        if not isinstance(name, str) or not name.strip():
            continue
        identifier = _unwrapped(stats.get("id"))
        source = _unwrapped(stats.get("source"))
        subclasses.append(
            {
                "identifier": identifier if isinstance(identifier, str) else "",
                "name": name.strip(),
                "source": source if isinstance(source, str) else default_source,
                "level": unlock_level,
            }
        )
    return unlock_level, subclasses


def _builder_entry_data(entry: CompendiumEntry) -> dict[str, object]:
    data = entry.data if isinstance(entry.data, dict) else {}
    stats = _unwrapped(data.get("stats"))
    sources = (data, stats if isinstance(stats, dict) else {})

    def choices(*keys: str) -> list[str]:
        labels = [
            label
            for source in sources
            for key in keys
            for label in _choice_labels(source.get(key))
        ]
        return list(dict.fromkeys(labels))

    subchoice_keys = (
        ("subraces", "subtypes", "choices")
        if entry.kind == CompendiumEntry.Kind.RACE
        else (
            "archetypes",
            "subclasses",
            "csubclasses",
            "subtypes",
            "subTypes",
            "choices",
        )
    )
    normalized: dict[str, object] = {
        "subchoices": choices(*subchoice_keys),
        "starting_equipment": choices(
            "starting_equipment", "startingEquipment", "selectable_equipments"
        ),
        "languages": choices("languages", "language_proficiencies"),
        "skill_proficiencies": choices("skill_proficiencies"),
        "armor_proficiencies": choices("armor_proficiencies"),
        "weapon_proficiencies": choices("weapon_proficiencies"),
        "tool_proficiencies": choices("tool_proficiencies"),
    }
    if entry.kind == CompendiumEntry.Kind.CLASS:
        unlock_level, subclasses = _class_subclasses(sources, entry.source.name)
        if subclasses:
            normalized["subclasses"] = subclasses
            normalized["subclass_selection_level"] = unlock_level
    return {key: value for key, value in normalized.items() if value}


def _level_up_rules(entry: CompendiumEntry, class_level: int) -> dict[str, object]:
    """Extract only the choices and gains relevant to one class level."""
    data = entry.data if isinstance(entry.data, dict) else {}
    stats = _unwrapped(data.get("stats"))
    sources = (data, stats if isinstance(stats, dict) else {})

    def detail(value: object) -> tuple[str, str, str]:
        value = _unwrapped(value)
        if not isinstance(value, dict):
            return "", "", ""
        feat = _unwrapped(value.get("feat"))
        row = feat if isinstance(feat, dict) else value
        name = _unwrapped(row.get("name"))
        identifier = _unwrapped(row.get("id"))
        descriptions = _unwrapped(row.get("descriptionModels"))
        description = ""
        if isinstance(descriptions, list):
            for item in descriptions:
                item = _unwrapped(item)
                if (
                    isinstance(item, dict)
                    and int(_unwrapped(item.get("level")) or 1) <= class_level
                ):
                    candidate = _unwrapped(item.get("description"))
                    if isinstance(candidate, str):
                        description = candidate
        return (
            name.strip() if isinstance(name, str) else "",
            identifier if isinstance(identifier, str) else "",
            description,
        )

    gains: list[dict[str, object]] = []
    prompts: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in sources:
        features = _unwrapped(source.get("features"))
        if isinstance(features, list):
            for row in features:
                row = _unwrapped(row)
                if (
                    not isinstance(row, dict)
                    or int(_unwrapped(row.get("level")) or 1) != class_level
                ):
                    continue
                name, identifier, description = detail(row)
                if name and (identifier or name) not in seen:
                    seen.add(identifier or name)
                    gains.append(
                        {
                            "name": name,
                            "identifier": identifier or name,
                            "description": description,
                        }
                    )
        selectable = _unwrapped(source.get("selectableFeatures"))
        if not isinstance(selectable, list):
            continue
        for index, row in enumerate(selectable):
            row = _unwrapped(row)
            if not isinstance(row, dict):
                continue
            amount = 0
            amounts = _unwrapped(row.get("amountsPerLevel"))
            if isinstance(amounts, list):
                for amount_row in amounts:
                    amount_row = _unwrapped(amount_row)
                    if (
                        isinstance(amount_row, dict)
                        and int(_unwrapped(amount_row.get("level")) or 0) == class_level
                    ):
                        amount = int(_unwrapped(amount_row.get("amount")) or 0)
            if not amount:
                continue
            options = []
            available = _unwrapped(row.get("availableFeatures"))
            if isinstance(available, list):
                for option in available:
                    name, identifier, description = detail(option)
                    if name:
                        options.append(
                            {
                                "name": name,
                                "identifier": identifier or name,
                                "description": description,
                            }
                        )
            prompts.append(
                {
                    "identifier": str(
                        _unwrapped(row.get("id")) or f"class-choice-{index}"
                    ),
                    "name": str(_unwrapped(row.get("name")) or "Class choice"),
                    "amount": amount,
                    "options": options,
                }
            )
    feature_asi = any(
        "ability score improvement" in str(gain["name"]).casefold() for gain in gains
    )
    default_asi_levels = {4, 8, 12, 16, 19}
    class_name = entry.name.casefold()
    if class_name == "fighter":
        default_asi_levels.update((6, 14))
    elif class_name == "rogue":
        default_asi_levels.add(10)
    return {
        "gains": gains,
        "choices": prompts,
        "ability_score_improvement": feature_asi or class_level in default_asi_levels,
    }


class HoardJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def encode_json(cls, content: object) -> str:
        return json.dumps(content, cls=DjangoJSONEncoder)


class ContextConsumer(HoardJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope["user"]
        context_id = int(self.scope["url_route"]["kwargs"]["context_id"])
        context_data = (
            await self._active_context_data(user.pk, context_id)
            if user.is_authenticated
            else None
        )
        if context_data is None:
            await self.close(code=4403)
            return
        self.context_id, self.campaign_id = context_data
        self.group_name = campaign_group_name(self.campaign_id)
        self.request_tasks: set[asyncio.Task[None]] = set()
        self.request_slots = asyncio.Semaphore(8)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        for task in tuple(getattr(self, "request_tasks", ())):
            task.cancel()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, object], **kwargs: object) -> None:
        message_type = content.get("type")
        if not isinstance(message_type, str):
            await self.send_json(
                {
                    "type": "error",
                    "code": "missing_type",
                    "detail": "A message type is required.",
                }
            )
            return
        request_id = content.get("request_id")
        if not is_uuid7(request_id):
            await self.send_json(
                {
                    "type": error_type(operation_kind(message_type)),
                    **({"request_id": request_id} if isinstance(request_id, str) else {}),
                    "code": "invalid_request_id",
                    "detail": "request_id must be a UUIDv7.",
                }
            )
            return
        handlers = {
            "campaign.get": self._campaign_get,
            "campaign.calendar.get": self._calendar_get,
            "campaign.calendar.adjust": self._calendar_adjust,
            "campaign.members.list": self._member_list,
            "campaign.members.deactivate": self._member_deactivate,
            "campaign.invites.list": self._invite_list,
            "campaign.invites.create": self._invite_create,
            "campaign.invites.resend": self._invite_resend,
            "campaign.invites.revoke": self._invite_revoke,
            "campaign.level.status": self._level_status,
            "campaign.level.approve": self._level_approve,
            "characters.list": self._character_list,
            "characters.get": self._character_get,
            "characters.create": self._character_create,
            "characters.update": self._character_update,
            "characters.archive": self._character_archive,
            "characters.builder.definition": self._builder_definition,
            "characters.builder.entry.get": self._builder_entry_get,
            "characters.builder.get": self._builder_get,
            "characters.builder.save": self._builder_save,
            "characters.builder.complete": self._builder_complete,
            "characters.level_up.definition": self._level_up_definition,
            "characters.level_up.class.get": self._level_up_class_get,
            "characters.level_up.preview": self._level_up_preview,
            "characters.level_up.complete": self._level_up_complete,
            "characters.level_up.feats": self._level_up_feats,
            "characters.health.post": self._health_post,
            "characters.notes.create": self._sheet_change,
            "characters.notes.update": self._sheet_change,
            "characters.notes.delete": self._sheet_change,
            "characters.features.create": self._sheet_change,
            "characters.features.update": self._sheet_change,
            "characters.features.delete": self._sheet_change,
            "characters.spells.create": self._sheet_change,
            "characters.spells.update": self._sheet_change,
            "characters.spells.delete": self._sheet_change,
            "characters.loadout.create": self._sheet_change,
            "characters.loadout.update": self._sheet_change,
            "characters.loadout.delete": self._sheet_change,
            "characters.effects.create": self._sheet_change,
            "characters.effects.update": self._sheet_change,
            "characters.effects.delete": self._sheet_change,
            "characters.spells.cast": self.spell_cast,
            "characters.rest": self.rest,
            "characters.inspiration.set": self.inspiration_set,
            "characters.companions.create": self._sheet_change,
            "characters.companions.update": self._sheet_change,
            "characters.companions.delete": self._sheet_change,
            "characters.imports.cah.begin": self._cah_begin,
            "characters.imports.cah.preview": self._cah_preview,
            "characters.imports.cah.commit": self._cah_commit,
            "characters.imports.cah.cancel": self._cah_cancel,
            "transactions.list": self._transaction_list,
            "inventory.transactions.create": self._inventory_transaction_create,
            "money.transfers.create": self._money_transfer_create,
            "money.exchanges.create": self._money_exchange_create,
            "experience.shared_awards.create": self._shared_xp_create,
            "transactions.reverse": self._transaction_reverse,
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
            task = asyncio.create_task(
                self._run_request(content, handler),
                name=f"campaign-request:{message_type}",
            )
            self.request_tasks.add(task)
            task.add_done_callback(self._request_finished)
            return
        if message_type != "compendium.repositories.import":
            await self.send_json(
                {
                    "type": "error",
                    "code": "unsupported_message",
                    "detail": "Unsupported message.",
                }
            )
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
                    "type": "command.error",
                    "request_id": request_id,
                    "code": "invalid_request",
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
                    "type": "command.error",
                    "request_id": request_id,
                    "code": "server_error",
                    "detail": "Unable to queue the repository import.",
                }
            )
            return
        if not queued:
            await self.send_json(
                {
                    "type": "command.error",
                    "request_id": request_id,
                    "code": "import_in_progress",
                    "detail": "A repository import is already running.",
                }
            )
            return
        await self.send_json(
            {"type": "command.ack", "request_id": request_id, "data": {"job_id": job_id}}
        )
        await self.send_json(
            {
                "type": "repository.import.started",
                "job_id": job_id,
                "request_id": request_id,
            }
        )

    async def _run_request(self, content: dict[str, object], handler) -> None:
        started = asyncio.get_running_loop().time()
        async with self.request_slots, ThreadSensitiveContext():
            await self._request_response(content, handler)
        elapsed = asyncio.get_running_loop().time() - started
        if elapsed >= 1:
            logger.warning(
                "Campaign request %s took %.3f seconds.", content.get("type"), elapsed
            )

    def _request_finished(self, task: asyncio.Task[None]) -> None:
        self.request_tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Unhandled error in campaign request task.",
                exc_info=(type(error), error, error.__traceback__),
            )

    async def domain_event(self, event: dict[str, object]) -> None:
        payload = event.get("event")
        if isinstance(payload, dict):
            await self.send_json(payload)

    async def repository_import_progress(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.progress", **event})

    async def repository_import_finished(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.finished", **event})

    async def repository_import_error(self, event: dict[str, object]) -> None:
        await self.send_json({"type": "repository.import.error", **event})

    async def _request_response(self, content: dict[str, object], handler) -> None:
        request_id = content.get("request_id")
        message_type = content.get("type")
        if not isinstance(message_type, str):
            return
        kind = operation_kind(message_type)
        try:
            envelope = RequestEnvelope.model_validate(
                {"type": message_type, "request_id": request_id}
            )
            definition = operation_definition(message_type)
            definition.payload_model.model_validate(
                {
                    key: value
                    for key, value in content.items()
                    if key not in {"type", "request_id"}
                }
            )
        except Exception:
            await self.send_json(
                RequestErrorEnvelope(
                    type=error_type(kind),
                    request_id=request_id if isinstance(request_id, str) else None,
                    code="invalid_request",
                    detail="The request envelope or payload is invalid.",
                ).model_dump(mode="json", exclude_none=True)
            )
            return
        try:
            data = await handler(content)
        except (HttpError, PermissionError, ValueError, ValidationError) as error:
            field_errors = getattr(error, "message_dict", None)
            detail = field_errors or getattr(error, "messages", None) or str(error)
            if isinstance(error, HttpError):
                code = f"http_{error.status_code}"
            elif isinstance(error, PermissionError):
                code = "forbidden"
            elif isinstance(error, ValidationError):
                code = "validation_error"
            else:
                code = "invalid_request"
            await self.send_json(
                RequestErrorEnvelope(
                    type=error_type(kind),
                    request_id=envelope.request_id,
                    code=code,
                    detail=detail,
                    field_errors=field_errors,
                ).model_dump(mode="json", exclude_none=True)
            )
            return
        except Exception:
            logger.exception(
                "Unable to process campaign request %s.", content.get("type")
            )
            await self.send_json(
                RequestErrorEnvelope(
                    type=error_type(kind),
                    request_id=envelope.request_id,
                    code="server_error",
                    detail="Unable to process the campaign request.",
                ).model_dump(mode="json")
            )
            return
        result_data = data
        if kind.value == "query" and definition.result_model is not None:
            result_data = definition.result_model.model_validate(data).model_dump(
                mode="json"
            )
        if kind.value == "query":
            response = QueryResultEnvelope(
                request_id=envelope.request_id,
                data=result_data,
            ).model_dump(mode="json")
        elif message_type in {
            "campaign.calendar.adjust",
            "campaign.members.deactivate",
            "campaign.invites.revoke",
            "campaign.level.approve",
            "characters.health.post",
            "characters.create",
            "characters.update",
            "characters.archive",
        }:
            response = CommandAcknowledgementEnvelope(
                request_id=envelope.request_id
            ).model_dump(mode="json")
        else:
            # Other command responses remain temporary compatibility payloads until
            # their domain event contracts are introduced by this foundation work.
            response = {
                "type": result_type(kind),
                "request_id": envelope.request_id,
                "data": data,
            }
        encoded = await self.encode_json(response)
        response_size = len(encoded.encode("utf-8"))
        if response_size > MAX_WEBSOCKET_RESPONSE_BYTES:
            logger.error(
                "Campaign request %s produced an oversized WebSocket response "
                "(%s bytes).",
                content.get("type"),
                response_size,
            )
            await self.send_json(
                {
                    "type": error_type(kind),
                    "request_id": request_id,
                    "code": "response_too_large",
                    "detail": (
                        "The campaign response was too large to send. "
                        "Please narrow the request and try again."
                    ),
                }
            )
            return
        await self.send(text_data=encoded)

    @database_sync_to_async
    def _active_context_data(self, user_id: int, context_id: int):
        return (
            CampaignContext.objects.filter(
                pk=context_id, user_id=user_id, is_active=True
            )
            .values_list("pk", "campaign_id")
            .first()
        )

    @database_sync_to_async
    def _campaign_get(self, content: dict[str, object]) -> dict[str, object]:
        from .api import (
            _character_data,
            _context_data,
            _party_money,
            _visible_characters,
        )

        context = self._context()
        campaign = context.campaign
        return {
            **_context_data(context),
            "id": campaign.pk,
            "name": campaign.name,
            "is_game_master": context.kind == CampaignContext.Kind.GM,
            "use_shared_exp": campaign.use_shared_exp,
            "shared_experience": campaign.shared_experience,
            "level": campaign.level,
            "eligible_level": Character.level_for_experience(
                campaign.shared_experience
            ),
            "calendar": CampaignCalendarData.from_campaign(campaign).model_dump(
                mode="json"
            ),
            "party_money": _party_money(campaign),
            "characters": [
                _character_data(value) for value in _visible_characters(context)
            ],
            "incomplete_level_ups": self._incomplete_level_ups(campaign),
        }

    @database_sync_to_async
    def _calendar_get(self, content: dict[str, object]) -> dict[str, object]:
        return CampaignCalendarData.from_campaign(
            self._context().campaign
        ).model_dump(mode="json")

    @database_sync_to_async
    def _calendar_adjust(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _gm

        context = self._context()
        _gm(context)
        amount = self._integer(content, "amount")
        CampaignCalendarService().adjust_day(context.campaign, amount)
        notify_campaign_event(
            context.campaign_id,
            CampaignCalendarChangedEvent(
                calendar=CampaignCalendarData.from_campaign(context.campaign),
                request_id=str(content["request_id"]),
            ),
        )
        return CampaignCalendarData.from_campaign(context.campaign).model_dump(
            mode="json"
        )

    @database_sync_to_async
    def _member_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import _gm

        context = self._context()
        _gm(context)
        return [
            {
                "id": candidate.pk,
                "username": candidate.user.get_username(),
                "is_game_master": candidate.kind == CampaignContext.Kind.GM,
                "is_active": candidate.is_active,
            }
            for candidate in CampaignContext.objects.filter(
                campaign=context.campaign
            ).select_related("user")
        ]

    @database_sync_to_async
    def _member_deactivate(self, content: dict[str, object]) -> None:
        from .api import _gm

        context = self._context()
        _gm(context)
        candidate = (
            CampaignContext.objects.filter(
                pk=self._integer(content, "member_id"),
                campaign=context.campaign,
                is_active=True,
            )
            .select_related("character")
            .first()
        )
        if candidate is None:
            raise HttpError(404, "Member not found.")
        before = {"kind": candidate.kind, "is_active": candidate.is_active}
        candidate.is_active = False
        candidate.save(update_fields=("is_active",))
        MembershipEvent.objects.create(
            campaign=context.campaign,
            created_by=context,
            subject=candidate,
            subject_user=candidate.user,
            reason=MembershipEvent.Reason.DEACTIVATED,
            before=before,
            after={"kind": candidate.kind, "is_active": False},
        )
        character = getattr(candidate, "character", None)
        if character:
            character.is_active = False
            character.is_archived = True
            character.archived_at = timezone.now()
            character.save(update_fields=("is_active", "is_archived", "archived_at"))
        notify_campaign_event(
            context.campaign_id,
            CampaignMembershipChangedEvent(
                member=CampaignMemberData(
                    id=candidate.pk,
                    username=candidate.user.get_username(),
                    is_game_master=candidate.kind == CampaignContext.Kind.GM,
                    is_active=candidate.is_active,
                ),
                request_id=str(content["request_id"]),
            ),
        )

    @database_sync_to_async
    def _invite_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import _gm

        context = self._context()
        _gm(context)
        return [
            self._invitation_data(value) for value in context.campaign.invitations.all()
        ]

    @database_sync_to_async
    def _invite_create(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _gm

        context = self._context()
        _gm(context)
        email = self._string(content, "email", maximum=254)
        invitation, token = create_invitation(context, email)
        link = self._invite_link(token)
        if email:
            send_mail(
                f"Invitation to {context.campaign.name}",
                f"Join the campaign: {link}",
                None,
                [email],
            )
        notify_campaign_event(
            context.campaign_id,
            CampaignInvitationChangedEvent(
                invitation=CampaignInvitationData.model_validate(
                    self._invitation_data(invitation)
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return {**self._invitation_data(invitation), "link": link}

    @database_sync_to_async
    def _invite_resend(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _gm
        from .services.invitations import token_digest

        context = self._context()
        _gm(context)
        invitation = context.campaign.invitations.filter(
            pk=self._integer(content, "invitation_id"),
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).first()
        if invitation is None:
            raise HttpError(404, "Active invitation not found.")
        token = secrets.token_urlsafe(32)
        invitation.token_digest = token_digest(token)
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save(update_fields=("token_digest", "expires_at"))
        InvitationEvent.objects.create(
            campaign=context.campaign,
            invitation=invitation,
            created_by=context,
            reason=InvitationEvent.Reason.RESENT,
        )
        link = self._invite_link(token)
        if invitation.delivery_email:
            send_mail(
                f"Invitation to {context.campaign.name}",
                f"Join the campaign: {link}",
                None,
                [invitation.delivery_email],
            )
        notify_campaign_event(
            context.campaign_id,
            CampaignInvitationChangedEvent(
                invitation=CampaignInvitationData.model_validate(
                    self._invitation_data(invitation)
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return {**self._invitation_data(invitation), "link": link}

    @database_sync_to_async
    def _invite_revoke(self, content: dict[str, object]) -> None:
        from .api import _gm

        context = self._context()
        _gm(context)
        invitation = context.campaign.invitations.filter(
            pk=self._integer(content, "invitation_id"),
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).first()
        if invitation is None:
            raise HttpError(404, "Active invitation not found.")
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=("revoked_at",))
        InvitationEvent.objects.create(
            campaign=context.campaign,
            invitation=invitation,
            created_by=context,
            reason=InvitationEvent.Reason.REVOKED,
        )
        notify_campaign_event(
            context.campaign_id,
            CampaignInvitationChangedEvent(
                invitation=CampaignInvitationData.model_validate(
                    self._invitation_data(invitation)
                ),
                request_id=str(content["request_id"]),
            ),
        )

    @database_sync_to_async
    def _level_status(self, content: dict[str, object]) -> dict[str, object]:
        campaign = self._context().campaign
        return {
            "level": campaign.level,
            "eligible_level": Character.level_for_experience(
                campaign.shared_experience
            ),
            "can_approve": campaign.level
            < Character.level_for_experience(campaign.shared_experience),
            "incomplete": self._incomplete_level_ups(campaign),
        }

    @database_sync_to_async
    def _level_approve(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _gm

        context = self._context()
        _gm(context)
        event = approve_campaign_level(context.campaign, created_by=context)
        notify_campaign_event(
            context.campaign_id,
            CampaignLevelChangedEvent(
                previous_level=event.previous_level,
                next_level=event.next_level,
                request_id=str(content["request_id"]),
            ),
        )
        return {
            "previous_level": event.previous_level,
            "next_level": event.next_level,
            "occurred_at": event.occurred_at.isoformat(),
            "campaign_date": event.campaign_date,
        }

    @database_sync_to_async
    def _character_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import _character_data, _visible_characters

        context = self._context()
        return [_character_data(value) for value in _visible_characters(context)]

    @database_sync_to_async
    def _character_get(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character, _character_data, _visible_characters

        context = self._context()
        character = _character(context, self._integer(content, "character_id"))
        if not _visible_characters(context).filter(pk=character.pk).exists():
            raise HttpError(404, "Character not found.")
        return _character_data(character)

    @database_sync_to_async
    def _character_create(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data, _gm

        context = self._context()
        _gm(context)
        fields = content.get("fields")
        if not isinstance(fields, dict) or not fields.get("is_npc"):
            raise ValidationError("Only NPC creation is available from this command.")
        character = CharacterLifecycleService().create_npc(context, fields)
        notify_campaign_event(
            context.campaign_id,
            CharacterLifecycleEvent(
                type="character.created",
                character=CharacterLifecycleData(
                    id=character.pk,
                    name=character.name,
                    is_active=character.is_active,
                    is_archived=character.is_archived,
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return _character_data(character)

    @database_sync_to_async
    def _character_update(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data, _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        fields = content.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("fields must be an object.")
        character = CharacterLifecycleService().update(context, character, fields)
        notify_campaign_event(
            context.campaign_id,
            CharacterLifecycleEvent(
                type="character.updated",
                character=CharacterLifecycleData(
                    id=character.pk,
                    name=character.name,
                    is_active=character.is_active,
                    is_archived=character.is_archived,
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return _character_data(character)

    @database_sync_to_async
    def _character_archive(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data, _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        character = CharacterLifecycleService().archive(context, character)
        notify_campaign_event(
            context.campaign_id,
            CharacterLifecycleEvent(
                type="character.archived",
                character=CharacterLifecycleData(
                    id=character.pk,
                    name=character.name,
                    is_active=character.is_active,
                    is_archived=character.is_archived,
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return _character_data(character)

    @database_sync_to_async
    def _builder_definition(self, content: dict[str, object]) -> dict[str, object]:
        context = self._context()
        entries = CompendiumEntry.objects.filter(
            source__in=context.campaign.compendium_sources.all(),
            kind__in=("race", "class", "background"),
        ).values(
            "pk",
            "kind",
            "source_identifier",
            "name",
            "source_book",
            "source__identifier",
            "source__name",
            "source__repository__identifier",
            "source__repository__name",
            "source__repository__campaign_id",
        )
        entries = sorted(
            entries,
            key=lambda row: (
                0
                if row["source__repository__campaign_id"] == context.campaign_id
                else 1
                if row["source__repository__identifier"] == "default"
                else 2,
                row["pk"],
            ),
        )
        grouped: dict[str, list[dict[str, object]]] = {
            "race": [],
            "class": [],
            "background": [],
        }
        canonical: dict[tuple[object, ...], dict[str, object]] = {}
        for entry in entries:
            identity = (
                entry["kind"],
                entry["source__identifier"],
                entry["source_identifier"],
            )
            if identity in canonical:
                canonical[identity]["alias_ids"].append(entry["pk"])
                continue
            value = {
                "id": entry["pk"],
                "alias_ids": [],
                "identifier": entry["source_identifier"],
                "name": entry["name"],
                "source": entry["source__name"],
                "source_book": entry["source_book"],
                "repository": entry["source__repository__name"],
                "repository_identifier": entry["source__repository__identifier"],
            }
            canonical[identity] = value
            grouped[entry["kind"]].append(value)
        for values in grouped.values():
            values.sort(key=lambda row: (str(row["name"]).lower(), row["id"]))
        return {
            **grouped,
            "level": context.campaign.level,
            "skills": [
                "acrobatics",
                "animal_handling",
                "arcana",
                "athletics",
                "deception",
                "history",
                "insight",
                "intimidation",
                "investigation",
                "medicine",
                "nature",
                "perception",
                "performance",
                "persuasion",
                "religion",
                "sleight_of_hand",
                "stealth",
                "survival",
            ],
        }

    @database_sync_to_async
    def _builder_entry_get(self, content: dict[str, object]) -> dict[str, object]:
        context = self._context()
        entry = (
            CompendiumEntry.objects.filter(
                pk=self._integer(content, "entry_id"),
                kind__in=("race", "class", "background"),
                source__in=context.campaign.compendium_sources.all(),
            )
            .select_related("source", "source__repository")
            .first()
        )
        if entry is None:
            raise ValidationError(
                "The selected builder entry is not enabled for this campaign."
            )
        return {
            "id": entry.pk,
            "kind": entry.kind,
            "identifier": entry.source_identifier,
            "name": entry.name,
            "source": entry.source.name,
            "source_book": entry.source_book,
            "repository": entry.source.repository.name,
            "repository_identifier": entry.source.repository.identifier,
            "data": _builder_entry_data(entry),
        }

    @database_sync_to_async
    def _builder_get(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data, _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        return {
            "character": _character_data(character),
            "class_levels": [
                {
                    "level": row.level,
                    "class_entry_id": row.class_entry_id,
                    "class_name": row.class_name,
                    "subclass_identifier": row.subclass_identifier,
                    "subclass_name": row.subclass_name,
                    "is_override": row.is_override,
                }
                for row in character.class_levels.all()
            ],
            "choices": [
                {
                    "level": row.level,
                    "origin_entry_id": row.origin_entry_id,
                    "identifier": row.identifier,
                    "kind": row.kind,
                    "values": row.values,
                    "is_override": row.is_override,
                }
                for row in character.build_choices.all()
            ],
        }

    @database_sync_to_async
    def _builder_save(self, content: dict[str, object]) -> dict[str, object]:
        from .api import SKILL_NAMES, _character_data, _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        before = character_snapshot(character)
        fields = content.get("fields", {})
        if not isinstance(fields, dict):
            raise ValueError("fields must be an object.")
        builder_fields = {
            "name",
            "race",
            "race_entry_id",
            "subrace_identifier",
            "subrace_name",
            "background",
            "background_entry_id",
            "alignment",
            "personality_traits",
            "ideals",
            "bonds",
            "flaws",
            "about",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
            "ability_bonuses",
            "ability_score_adjustments",
            "languages",
            "equipment_proficiencies",
            "skill_proficiencies",
            "base_hp",
            "hp_ability",
            "hp_adjustment",
        }
        unknown = set(fields) - builder_fields
        if unknown:
            raise ValueError(
                f"Unsupported builder fields: {', '.join(sorted(unknown))}"
            )
        skills = fields.get("skill_proficiencies")
        if skills is not None and (
            not isinstance(skills, dict)
            or set(skills) - set(SKILL_NAMES)
            or set(skills.values()) - {"none", "half", "proficient", "expertise"}
        ):
            raise ValidationError("Skill proficiencies contain an invalid choice.")
        if "languages" in fields and not (
            isinstance(fields["languages"], list)
            and all(isinstance(value, str) for value in fields["languages"])
        ):
            raise ValidationError("Languages must be a list of names.")
        if fields.get("hp_ability", "constitution") not in {
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        }:
            raise ValidationError("HP ability is invalid.")
        for field_name, kind in (
            ("race_entry_id", "race"),
            ("background_entry_id", "background"),
        ):
            if field_name in fields and fields[field_name] is not None:
                entry = self._enabled_builder_entry(context, fields[field_name], kind)
                fields[field_name] = entry.pk
        for key, value in fields.items():
            setattr(character, key, value)
        class_levels = content.get("class_levels")
        choices = content.get("choices")
        with transaction.atomic():
            character.full_clean()
            character.save()
            if isinstance(class_levels, list):
                character.class_levels.all().delete()
                for row in class_levels:
                    if not isinstance(row, dict):
                        raise ValueError("Each class level must be an object.")
                    level = int(row.get("level", 0))
                    if not 1 <= level <= context.campaign.level:
                        raise ValueError("Class levels must match the campaign level.")
                    entry_id = row.get("class_entry_id")
                    entry = (
                        self._enabled_builder_entry(context, entry_id, "class")
                        if entry_id
                        else None
                    )
                    CharacterClassLevel.objects.create(
                        character=character,
                        level=level,
                        class_entry=entry,
                        class_name=str(
                            row.get("class_name") or (entry.name if entry else "")
                        ),
                        subclass_identifier=str(row.get("subclass_identifier") or ""),
                        subclass_name=str(row.get("subclass_name") or ""),
                        is_override=bool(row.get("is_override")),
                    )
                character.character_class = self._class_summary(character)
                character.save(update_fields=("character_class",))
            if isinstance(choices, list):
                character.build_choices.all().delete()
                for row in choices:
                    if not isinstance(row, dict):
                        raise ValueError("Each builder choice must be an object.")
                    level = int(row.get("level", 1))
                    if not 1 <= level <= context.campaign.level:
                        raise ValueError("Choice levels must match the campaign level.")
                    CharacterChoice.objects.create(
                        character=character,
                        level=level,
                        origin_entry_id=row.get("origin_entry_id"),
                        identifier=str(row.get("identifier") or ""),
                        kind=str(row.get("kind") or "custom"),
                        values=row.get("values", []),
                        is_override=bool(row.get("is_override")),
                    )
            record_character_history(
                character,
                reason=CharacterHistory.Reason.OVERRIDE
                if bool(content.get("is_override"))
                else CharacterHistory.Reason.EDIT,
                before=before,
                created_by=context,
                description=self._string(content, "description"),
            )
        notify_campaign_changed(context.campaign_id)
        return _character_data(character)

    @database_sync_to_async
    def _builder_complete(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data, _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        if not character.name.strip() or not character.race.strip():
            raise ValidationError("Name and race are required.")
        levels = list(character.class_levels.order_by("level"))
        if [row.level for row in levels] != list(range(1, context.campaign.level + 1)):
            raise ValidationError("Choose one class for every campaign level.")
        if any(not row.class_name.strip() for row in levels):
            raise ValidationError("Every campaign level requires a class choice.")
        before = character_snapshot(character)
        was_initial_build = not character.is_build_complete
        was_imported = character.history.filter(
            reason=CharacterHistory.Reason.IMPORT
        ).exists()
        is_level_up = character.level_progress.filter(
            level=context.campaign.level, is_complete=False
        ).exists()
        with transaction.atomic():
            character.is_build_complete = True
            character.character_class = self._class_summary(character)
            character.save(update_fields=("is_build_complete", "character_class"))
            for level in range(1, context.campaign.level + 1):
                CharacterLevelProgress.objects.update_or_create(
                    character=character,
                    level=level,
                    defaults={"is_complete": True, "completed_at": timezone.now()},
                )
            character = character.activate()
            if (
                was_initial_build
                and not was_imported
                and character.current_hp != character.max_hp
            ):
                post_health_transaction(
                    character,
                    reason=HealthTransaction.Reason.CORRECTION,
                    current_hp=character.max_hp,
                    temporary_hp=character.temporary_hp,
                    description="Completed initial character build",
                    created_by=context,
                )
                character.refresh_from_db()
            record_character_history(
                character,
                reason=(
                    CharacterHistory.Reason.LEVEL_UP
                    if is_level_up
                    else CharacterHistory.Reason.CREATE
                ),
                before=before,
                created_by=context,
                description=(
                    f"Completed level {context.campaign.level} level up"
                    if is_level_up
                    else "Completed character builder"
                ),
            )
        notify_campaign_changed(context.campaign_id)
        return _character_data(character)

    def _pending_level_up(self, context, character_id: int):
        from .api import _editable_sheet_character

        character = _editable_sheet_character(context, character_id)
        if not character.is_player_character or not character.is_active:
            raise ValidationError(
                "Level-up is only available for active player characters."
            )
        progress = character.level_progress.filter(
            level=context.campaign.level, is_complete=False
        ).first()
        if progress is None:
            raise ValidationError("This character has no pending level-up.")
        return character, progress

    @staticmethod
    def _hit_die(entry: CompendiumEntry) -> int:
        data = entry.data if isinstance(entry.data, dict) else {}
        stats = _unwrapped(data.get("stats"))
        for source in (data, stats if isinstance(stats, dict) else {}):
            for key in ("hit_die", "hitDie", "hit_dice", "hitDice"):
                value = _unwrapped(source.get(key))
                if isinstance(value, int) and value > 0:
                    return value
                if isinstance(value, str):
                    digits = "".join(
                        character for character in value if character.isdigit()
                    )
                    if digits:
                        return int(digits)
        return 8

    @database_sync_to_async
    def _level_up_definition(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data

        context = self._context()
        character, _ = self._pending_level_up(
            context, self._integer(content, "character_id")
        )
        classes = list(
            CompendiumEntry.objects.filter(
                kind=CompendiumEntry.Kind.CLASS,
                source__in=context.campaign.compendium_sources.all(),
            )
            .select_related("source", "source__repository")
            .order_by("name", "pk")
        )
        entries_by_id = {entry.pk: entry for entry in classes}
        entries_by_name = {entry.name.casefold(): entry for entry in classes}
        preferred_class_ids: list[int] = []
        for row in character.class_levels.order_by("-level"):
            entry = entries_by_id.get(row.class_entry_id) or entries_by_name.get(
                row.class_name.casefold()
            )
            if entry is not None and entry.pk not in preferred_class_ids:
                preferred_class_ids.append(entry.pk)
        return {
            "character": _character_data(character),
            "level": context.campaign.level,
            "preferred_class_ids": preferred_class_ids,
            "classes": [
                {
                    "id": entry.pk,
                    "name": entry.name,
                    "source": entry.source.name,
                    "source_book": entry.source_book,
                    "identifier": entry.source_identifier,
                }
                for entry in classes
            ],
        }

    @database_sync_to_async
    def _level_up_feats(self, content: dict[str, object]) -> list[dict[str, object]]:
        context = self._context()
        # The character guard prevents this from becoming a general large
        # Compendium response and keeps the feat picker scoped to a level-up.
        self._pending_level_up(context, self._integer(content, "character_id"))
        query = self._string(content, "query")
        entries = CompendiumEntry.objects.filter(
            kind=CompendiumEntry.Kind.FEAT,
            source__in=context.campaign.compendium_sources.all(),
        ).select_related("source")
        if query:
            entries = entries.filter(name__icontains=query)
        return [
            {
                "id": entry.pk,
                "name": entry.name,
                "source": entry.source.name,
                "source_book": entry.source_book,
            }
            for entry in entries.order_by("name")[:100]
        ]

    def _level_up_data(
        self, context, character, entry: CompendiumEntry
    ) -> dict[str, object]:
        existing = character.class_levels.filter(class_entry=entry).count()
        class_level = existing + 1
        rules = _level_up_rules(entry, class_level)
        entry_data = _builder_entry_data(entry)
        subclass_level = entry_data.get("subclass_selection_level")
        needs_subclass = (
            isinstance(subclass_level, int)
            and subclass_level == class_level
            and not character.class_levels.filter(
                class_entry=entry,
                subclass_identifier__gt="",
            ).exists()
        )
        return {
            "class": {
                "id": entry.pk,
                "name": entry.name,
                "source": entry.source.name,
                "source_book": entry.source_book,
                "class_level": class_level,
                "hit_die": self._hit_die(entry),
                "average_hp": self._hit_die(entry) // 2 + 1,
                "subclass_required": needs_subclass,
                "subclasses": entry_data.get("subclasses", [])
                if needs_subclass
                else [],
            },
            **rules,
        }

    @database_sync_to_async
    def _level_up_class_get(self, content: dict[str, object]) -> dict[str, object]:
        context = self._context()
        character, _ = self._pending_level_up(
            context, self._integer(content, "character_id")
        )
        entry = self._enabled_builder_entry(
            context, self._integer(content, "class_entry_id"), "class"
        )
        return self._level_up_data(context, character, entry)

    @database_sync_to_async
    def _level_up_preview(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data

        context = self._context()
        character, _ = self._pending_level_up(
            context, self._integer(content, "character_id")
        )
        entry = self._enabled_builder_entry(
            context, self._integer(content, "class_entry_id"), "class"
        )
        before = _character_data(character)["sheet"]
        hp_increase = self._nonnegative_integer(content, "hp_increase")
        adjustments = content.get("ability_adjustments", {})
        if (
            not isinstance(adjustments, dict)
            or set(adjustments)
            - {
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            }
            or not all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in adjustments.values()
            )
        ):
            raise ValidationError("Ability adjustments are invalid.")
        original_base_hp = character.base_hp
        original_adjustments = character.ability_score_adjustments
        character.base_hp += hp_increase
        character.ability_score_adjustments = {
            **original_adjustments,
            **{
                key: int(original_adjustments.get(key, 0)) + value
                for key, value in adjustments.items()
            },
        }
        after = _character_data(character)["sheet"]
        character.base_hp = original_base_hp
        character.ability_score_adjustments = original_adjustments
        return {
            "rules": self._level_up_data(context, character, entry),
            "before": before,
            "after": after,
        }

    @database_sync_to_async
    def _level_up_complete(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character_data

        context = self._context()
        character, progress = self._pending_level_up(
            context, self._integer(content, "character_id")
        )
        if character.class_levels.filter(level=context.campaign.level).exists():
            raise ValidationError("This campaign level already has a class allocation.")
        entry = self._enabled_builder_entry(
            context, self._integer(content, "class_entry_id"), "class"
        )
        method = self._string(content, "hp_method", required=True)
        if method not in {"roll", "average"}:
            raise ValidationError("HP method must be roll or average.")
        hp_increase = self._positive_integer(content, "hp_increase", default=0)
        hit_die = self._hit_die(entry)
        if method == "roll" and hp_increase > hit_die:
            raise ValidationError("HP roll cannot exceed the class hit die.")
        if method == "average" and hp_increase != hit_die // 2 + 1:
            raise ValidationError("HP average does not match the selected class.")
        adjustments = content.get("ability_adjustments", {})
        if (
            not isinstance(adjustments, dict)
            or set(adjustments)
            - {
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            }
            or not all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in adjustments.values()
            )
        ):
            raise ValidationError("Ability adjustments are invalid.")
        choices = content.get("choices", [])
        if not isinstance(choices, list):
            raise ValidationError("Level-up choices must be a list.")
        before = character_snapshot(character)
        subclass_identifier = self._string(content, "subclass_identifier", maximum=200)
        subclass_name = self._string(content, "subclass_name", maximum=200)
        rule_data = self._level_up_data(context, character, entry)
        class_data = rule_data["class"]
        if class_data["subclass_required"] and not (
            subclass_identifier or subclass_name
        ):
            raise ValidationError("Choose a subclass or provide a custom override.")
        submitted_choices = {
            str(row.get("identifier")): row
            for row in choices
            if isinstance(row, dict) and isinstance(row.get("identifier"), str)
        }
        for prompt in rule_data["choices"]:
            identifier = str(prompt["identifier"])
            selected = submitted_choices.get(identifier, {}).get("values", [])
            custom = submitted_choices.get(f"custom:{identifier}", {}).get("values", [])
            if not isinstance(selected, list) or not isinstance(custom, list):
                raise ValidationError("Level-up choices must use lists of values.")
            if len(selected) < int(prompt["amount"]) and not custom:
                raise ValidationError(
                    f"Choose {prompt['name']} or provide a custom override."
                )
        asi_choice = self._string(content, "asi_choice")
        adjustment_total = sum(adjustments.values())
        feat_entry = None
        feat_override = self._string(content, "feat_override", maximum=200)
        if rule_data["ability_score_improvement"]:
            if asi_choice not in {"scores", "feat"}:
                raise ValidationError("Choose ability scores or a feat for this ASI.")
            if asi_choice == "scores":
                if adjustment_total != 2 or any(
                    value < 0 or value > 2 for value in adjustments.values()
                ):
                    raise ValidationError(
                        "An ASI must distribute exactly two points, with no score receiving more than two."
                    )
            else:
                if adjustment_total:
                    raise ValidationError(
                        "A feat cannot also spend ASI ability points."
                    )
                feat_entry_id = content.get("feat_entry_id")
                if isinstance(feat_entry_id, int) and not isinstance(
                    feat_entry_id, bool
                ):
                    feat_entry = self._enabled_builder_entry(
                        context, feat_entry_id, "feat"
                    )
                if feat_entry is None and not feat_override:
                    raise ValidationError(
                        "Choose a feat or provide a custom feat override."
                    )
        elif (
            adjustment_total
            or asi_choice
            or content.get("feat_entry_id")
            or feat_override
        ):
            raise ValidationError(
                "This class level does not grant an ability score improvement."
            )
        with transaction.atomic():
            CharacterClassLevel.objects.create(
                character=character,
                level=context.campaign.level,
                class_entry=entry,
                class_name=entry.name,
                subclass_identifier=subclass_identifier,
                subclass_name=subclass_name,
                is_override=bool(content.get("class_override")),
            )
            character.base_hp += hp_increase
            character.ability_score_adjustments = {
                **character.ability_score_adjustments,
                **{
                    key: int(character.ability_score_adjustments.get(key, 0)) + value
                    for key, value in adjustments.items()
                },
            }
            character.character_class = self._class_summary(character)
            character.save(
                update_fields=(
                    "base_hp",
                    "ability_score_adjustments",
                    "character_class",
                )
            )
            for row in choices:
                if not isinstance(row, dict):
                    raise ValidationError("Each level-up choice must be an object.")
                identifier = str(row.get("identifier") or "").strip()
                if not identifier:
                    raise ValidationError("Each level-up choice needs an identifier.")
                CharacterChoice.objects.update_or_create(
                    character=character,
                    level=context.campaign.level,
                    identifier=identifier,
                    defaults={
                        "origin_entry": entry,
                        "kind": str(row.get("kind") or "class_choice"),
                        "values": row.get("values", []),
                        "is_override": bool(row.get("is_override")),
                    },
                )
            if rule_data["ability_score_improvement"] and asi_choice == "feat":
                CharacterChoice.objects.update_or_create(
                    character=character,
                    level=context.campaign.level,
                    identifier="asi-feat",
                    defaults={
                        "origin_entry": feat_entry,
                        "kind": "feat",
                        "values": [feat_entry.name if feat_entry else feat_override],
                        "is_override": feat_entry is None,
                    },
                )
            progress.hp_method = method
            progress.hp_base_increase = hp_increase
            progress.is_complete = True
            progress.completed_at = timezone.now()
            progress.save(
                update_fields=(
                    "hp_method",
                    "hp_base_increase",
                    "is_complete",
                    "completed_at",
                )
            )
            post_health_transaction(
                character,
                reason=HealthTransaction.Reason.HEALING,
                current_hp_delta=hp_increase,
                description=f"Level {context.campaign.level} HP increase",
                created_by=context,
            )
            character.refresh_from_db()
            record_character_history(
                character,
                reason=CharacterHistory.Reason.LEVEL_UP,
                before=before,
                created_by=context,
                description=f"Completed level {context.campaign.level} level up",
            )
        notify_campaign_changed(context.campaign_id)
        return _character_data(character)

    @database_sync_to_async
    def _health_post(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _character, _is_owner

        context = self._context()
        character = _character(context, self._integer(content, "character_id"))
        if context.kind != CampaignContext.Kind.GM and not _is_owner(
            context, character
        ):
            raise PermissionError("You may only change your own character's HP.")
        posted = CharacterHealthService().post(
            character,
            reason=self._string(content, "reason", required=True),
            current_hp_delta=int(content.get("current_hp_delta", 0)),
            temporary_hp_delta=int(content.get("temporary_hp_delta", 0)),
            current_hp=content.get("current_hp")
            if isinstance(content.get("current_hp"), int)
            else None,
            temporary_hp=content.get("temporary_hp")
            if isinstance(content.get("temporary_hp"), int)
            else None,
            description=self._string(content, "description"),
            created_by=context,
        )
        character.refresh_from_db(fields=("current_hp", "temporary_hp"))
        notify_campaign_event(
            context.campaign_id,
            CharacterHealthChangedEvent(
                character_id=character.pk,
                current_hp=character.current_hp,
                temporary_hp=character.temporary_hp,
                request_id=str(content["request_id"]),
            ),
        )
        return self._health_data(posted)

    @database_sync_to_async
    def _sheet_change(self, content: dict[str, object]) -> dict[str, object] | None:
        from types import SimpleNamespace

        from . import api

        context = self._context()
        character_id = self._integer(content, "character_id")
        character = api._editable_sheet_character(context, character_id)
        command = self._string(content, "type", required=True)
        operation = command.rsplit(".", 1)[-1]
        resource = command.split(".")[1]
        functions = {
            ("notes", "create"): api.note_create,
            ("notes", "update"): api.note_update,
            ("notes", "delete"): api.note_delete,
            ("features", "create"): api.feature_create,
            ("features", "update"): api.feature_update,
            ("features", "delete"): api.feature_delete,
            ("spells", "create"): api.spell_create,
            ("spells", "update"): api.spell_update,
            ("spells", "delete"): api.spell_delete,
            ("loadout", "create"): api.loadout_create,
            ("loadout", "update"): api.loadout_update,
            ("loadout", "delete"): api.loadout_delete,
            ("effects", "create"): api.effect_create,
            ("effects", "update"): api.effect_update,
            ("effects", "delete"): api.effect_delete,
            ("companions", "create"): api.companion_create,
            ("companions", "update"): api.companion_update,
            ("companions", "delete"): api.companion_delete,
        }
        handler = functions[(resource, operation)]
        request = SimpleNamespace(auth=context.user)
        if operation == "delete":
            result = handler(
                request,
                context.pk,
                character_id,
                self._integer(content, "record_id"),
            )
        else:
            fields = content.get("fields", {})
            if not isinstance(fields, dict):
                raise ValueError("fields must be an object.")
            payload = api.SheetRecord(**fields)
            arguments = [request, context.pk, character_id]
            if operation == "update":
                arguments.append(self._integer(content, "record_id"))
            result = handler(*arguments, payload)
        CharacterHistory.objects.create(
            campaign=context.campaign,
            character=character,
            created_by=context,
            reason=CharacterHistory.Reason.EDIT,
            description=f"{operation.title()} {resource}",
            changes={
                "sheet": {
                    "resource": resource,
                    "operation": operation,
                    "record_id": content.get("record_id"),
                }
            },
        )
        notify_campaign_changed(context.campaign_id)
        if isinstance(result, tuple):
            return result[1]

    @database_sync_to_async
    def spell_cast(self, content: dict[str, object]) -> dict[str, object]:
        from . import api

        context = self._context()
        character = api._editable_sheet_character(context, self._integer(content, "character_id"))
        slot = content.get("slot")
        if slot is not None and not isinstance(slot, str):
            raise ValueError("slot must be a string.")
        result = api.cast_spell(character, self._integer(content, "spell_id"), slot, created_by=context)
        notify_campaign_changed(context.campaign_id)
        return result

    @database_sync_to_async
    def rest(self, content: dict[str, object]) -> dict[str, object]:
        from . import api

        context = self._context()
        character = api._editable_sheet_character(context, self._integer(content, "character_id"))
        kind = self._string(content, "kind", required=True)
        if kind not in {"short", "long"}:
            raise ValueError("kind must be short or long.")
        current_hp = content.get("current_hp")
        if current_hp is not None and not isinstance(current_hp, int):
            raise ValueError("current_hp must be an integer.")
        result = api.take_rest(character, kind, current_hp, created_by=context)
        notify_campaign_changed(context.campaign_id)
        return result

    @database_sync_to_async
    def inspiration_set(self, content: dict[str, object]) -> dict[str, object]:
        from . import api

        context = self._context()
        character = api._editable_sheet_character(context, self._integer(content, "character_id"))
        available = content.get("available")
        if not isinstance(available, bool):
            raise ValueError("available must be a boolean.")
        result = api.set_inspiration(character, available, created_by=context)
        notify_campaign_changed(context.campaign_id)
        return result
        return result

    @database_sync_to_async
    def _transaction_list(self, content: dict[str, object]) -> dict[str, object]:
        from .api import TRANSACTION_MODELS, _history_data, _transaction_queryset

        context = self._context()
        ledger = self._string(content, "ledger") or "all"
        rows: list[dict[str, object]] = []
        if ledger in ("all", "inventory", "money", "experience"):
            choices = (
                TRANSACTION_MODELS.items()
                if ledger == "all"
                else ((ledger, TRANSACTION_MODELS[ledger]),)
            )
            for _, model in choices:
                query = _transaction_queryset(model, context.campaign)
                if context.kind != CampaignContext.Kind.GM:
                    query = query.filter(
                        entries__account__character__context__user=context.user
                    ).distinct()
                rows.extend(_history_data(posted) for posted in query)
        if ledger in ("all", "health"):
            health = HealthTransaction.objects.filter(
                campaign=context.campaign
            ).select_related("character", "created_by__user")
            if context.kind != CampaignContext.Kind.GM:
                health = health.filter(character__context__user=context.user)
            rows.extend(self._health_data(posted) for posted in health)
        if ledger in ("all", "character"):
            history = CharacterHistory.objects.filter(
                campaign=context.campaign
            ).select_related("character", "created_by__user")
            if context.kind != CampaignContext.Kind.GM:
                history = history.filter(character__context__user=context.user)
            rows.extend(self._character_history_data(posted) for posted in history)
        if ledger in ("all", "audit"):
            audit_models = [CampaignLevelEvent]
            if context.kind == CampaignContext.Kind.GM:
                audit_models.extend((InvitationEvent, MembershipEvent))
            for model in audit_models:
                events = model.objects.filter(campaign=context.campaign).select_related(
                    "created_by__user"
                )
                rows.extend(self._audit_data(posted) for posted in events)
        rows.sort(key=lambda row: str(row["occurred_at"]), reverse=True)
        page = max(1, int(content.get("page", 1)))
        page_size = min(100, max(1, int(content.get("page_size", 25))))
        start = (page - 1) * page_size
        return {
            "count": len(rows),
            "page": page,
            "page_size": page_size,
            "results": rows[start : start + page_size],
        }

    @database_sync_to_async
    def _inventory_transaction_create(
        self, content: dict[str, object]
    ) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import InventoryTransactionCreate, inventory_transaction_create

        context = self._context()
        payload = InventoryTransactionCreate(
            from_character_id=content.get("from_character_id"),
            to_character_id=content.get("to_character_id"),
            item_id=self._integer(content, "item_id"),
            quantity=self._integer(content, "quantity"),
            description=self._string(content, "description"),
        )
        result = inventory_transaction_create(
            SimpleNamespace(auth=context.user), context.pk, payload
        )
        return result[1] if isinstance(result, tuple) else result

    @database_sync_to_async
    def _money_transfer_create(self, content: dict[str, object]) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import MoneyTransferCreate, money_transfer_create

        context = self._context()
        payload = MoneyTransferCreate(
            from_character_id=content.get("from_character_id"),
            to_character_id=content.get("to_character_id"),
            amounts=content.get("amounts", {}),
            description=self._string(content, "description"),
        )
        result = money_transfer_create(
            SimpleNamespace(auth=context.user), context.pk, payload
        )
        return result[1] if isinstance(result, tuple) else result

    @database_sync_to_async
    def _money_exchange_create(self, content: dict[str, object]) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import MoneyExchangeCreate, money_exchange_create

        context = self._context()
        payload = MoneyExchangeCreate(
            character_id=self._integer(content, "character_id"),
            given=content.get("given", {}),
            received=content.get("received", {}),
            description=self._string(content, "description"),
        )
        result = money_exchange_create(
            SimpleNamespace(auth=context.user), context.pk, payload
        )
        return result[1] if isinstance(result, tuple) else result

    @database_sync_to_async
    def _shared_xp_create(self, content: dict[str, object]) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import SharedXpAwardCreate, shared_xp_award_create

        context = self._context()
        payload = SharedXpAwardCreate(
            amount=self._integer(content, "amount"),
            description=self._string(content, "description"),
        )
        result = shared_xp_award_create(
            SimpleNamespace(auth=context.user), context.pk, payload
        )
        return result[1] if isinstance(result, tuple) else result

    @database_sync_to_async
    def _transaction_reverse(self, content: dict[str, object]) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import transaction_reverse

        context = self._context()
        return transaction_reverse(
            SimpleNamespace(auth=context.user),
            context.pk,
            self._string(content, "ledger", required=True),
            self._integer(content, "transaction_id"),
        )

    @database_sync_to_async
    def _cah_begin(self, content: dict[str, object]) -> dict[str, object]:
        from .api import _editable_sheet_character

        context = self._context()
        character = _editable_sheet_character(
            context, self._integer(content, "character_id")
        )
        upload_id = secrets.token_urlsafe(24)
        cache.set(
            f"cah-upload:{upload_id}",
            {
                "user_id": context.user_id,
                "context_id": context.pk,
                "campaign_id": context.campaign_id,
                "character_id": character.pk,
            },
            timeout=900,
        )
        return {
            "upload_id": upload_id,
            "upload_url": f"/api/uploads/character-imports/{upload_id}/",
            "expires_in": 900,
        }

    @database_sync_to_async
    def _cah_preview(self, content: dict[str, object]) -> dict[str, object]:
        from .api import (
            _calculated_values,
            _import_entry_index,
            _match_import_entry,
        )
        from .services.cah import parse_cah

        context = self._context()
        upload_id = self._string(content, "upload_id", required=True)
        metadata = cache.get(f"cah-upload:{upload_id}")
        raw = cache.get(f"cah-upload-bytes:{upload_id}")
        if (
            not metadata
            or metadata.get("context_id") != context.pk
            or not isinstance(raw, bytes)
        ):
            raise ValidationError("This upload is missing, expired, or incomplete.")
        preview = parse_cah(raw)
        target = Character.objects.get(
            pk=metadata["character_id"], campaign=context.campaign
        )
        entry_index = _import_entry_index(context.campaign)
        inventory = [
            {
                **row,
                "matched_item_id": _match_import_entry(
                    context.campaign, row, entry_index
                ),
            }
            for row in preview.inventory
        ]
        candidate = Character.objects.get(pk=target.pk)
        for name, value in preview.fields.items():
            if name not in {"current_hp", "temporary_hp"}:
                setattr(candidate, name, value)
        token = secrets.token_urlsafe(24)
        cache.set(
            f"cah-import:{context.user_id}:{token}",
            {
                "campaign_id": context.campaign_id,
                "fields": preview.fields,
                "collections": preview.collections,
                "inventory": inventory,
                "warnings": preview.warnings,
            },
            timeout=900,
        )
        cache.delete_many((f"cah-upload:{upload_id}", f"cah-upload-bytes:{upload_id}"))
        # Keep complete source records in the server-side draft for commit. Raw 5e
        # Companion records are highly repetitive and can make the public preview
        # many times larger than the uploaded file, exceeding Daphne's frame limit.
        public_inventory = [
            {
                **{key: value for key, value in row.items() if key != "raw"},
                "suggested_item_id": row["matched_item_id"],
            }
            for row in inventory
        ]
        field_changes = [
            {
                "field": name,
                "before": getattr(target, name, None),
                "after": value,
                "changed": getattr(target, name, None) != value,
            }
            for name, value in preview.fields.items()
        ]
        collection_managers = {
            "notes": target.notes,
            "features": target.features,
            "spells": target.spells,
            "companions": target.companions,
        }
        collection_changes = [
            {
                "collection": name,
                "before_count": manager.count(),
                "after_count": len(preview.collections[name]),
                "names": [
                    str(row.get("name") or row.get("title") or "Untitled")
                    for row in preview.collections[name][:10]
                ],
                "remaining_count": max(0, len(preview.collections[name]) - 10),
            }
            for name, manager in collection_managers.items()
            if manager.exists() or preview.collections[name]
        ]
        return {
            "token": token,
            "field_changes": field_changes,
            "collection_changes": collection_changes,
            "inventory": public_inventory,
            "warnings": preview.warnings,
            "calculated_before": _calculated_values(target),
            "calculated_after": _calculated_values(candidate),
        }

    @database_sync_to_async
    def _cah_commit(self, content: dict[str, object]) -> dict[str, object]:
        from types import SimpleNamespace

        from .api import CahCommit, cah_commit

        context = self._context()
        character_id = self._integer(content, "character_id")
        character = Character.objects.get(pk=character_id, campaign=context.campaign)
        before = character_snapshot(character)
        before_current, before_temporary = character.current_hp, character.temporary_hp
        token = self._string(content, "token", required=True)
        cache_key = f"cah-import:{context.user_id}:{token}"
        draft = cache.get(cache_key)
        if not draft:
            raise ValidationError("This import preview has expired or is invalid.")
        draft = {**draft, "fields": dict(draft["fields"])}
        overrides = content.get("fields", {})
        excluded_fields = content.get("excluded_fields", [])
        if not isinstance(overrides, dict) or not isinstance(excluded_fields, list):
            raise ValidationError(
                "Import overrides must contain fields and exclusions."
            )
        available_fields = set(draft["fields"])
        if set(overrides) - available_fields or any(
            not isinstance(name, str) or name not in available_fields
            for name in excluded_fields
        ):
            raise ValidationError(
                "An import override targets a field not in this preview."
            )
        for name in excluded_fields:
            draft["fields"].pop(name, None)
        draft["fields"].update(overrides)
        collection_choices = content.get("collections", {})
        if (
            not isinstance(collection_choices, dict)
            or set(collection_choices) - set(draft["collections"])
            or not all(isinstance(value, bool) for value in collection_choices.values())
        ):
            raise ValidationError("Import collection choices are invalid.")
        imported_current = draft["fields"].pop("current_hp", before_current)
        imported_temporary = draft["fields"].pop("temporary_hp", before_temporary)
        cache.set(cache_key, draft, timeout=900)
        payload = CahCommit(
            token=token,
            character_id=character_id,
            inventory=content.get("inventory", []),
            collections=collection_choices,
        )
        cah_commit(SimpleNamespace(auth=context.user), context.pk, payload)
        character.refresh_from_db()
        if imported_current != before_current or imported_temporary != before_temporary:
            post_health_transaction(
                character,
                reason=HealthTransaction.Reason.CORRECTION,
                current_hp=imported_current,
                temporary_hp=imported_temporary,
                description="Imported from 5e Companion",
                created_by=context,
            )
            character.refresh_from_db()
        record_character_history(
            character,
            reason=CharacterHistory.Reason.IMPORT,
            before=before,
            created_by=context,
            description="Imported from 5e Companion",
        )
        from .api import _character_data

        return _character_data(character)

    @database_sync_to_async
    def _cah_cancel(self, content: dict[str, object]) -> None:
        upload_id = self._string(content, "upload_id")
        if upload_id:
            metadata = cache.get(f"cah-upload:{upload_id}")
            if metadata and metadata.get("context_id") == self.context_id:
                cache.delete_many(
                    (f"cah-upload:{upload_id}", f"cah-upload-bytes:{upload_id}")
                )
        token = self._string(content, "token")
        if token:
            cache.delete(f"cah-import:{self.scope['user'].pk}:{token}")

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
                pk=self.context_id,
                user_id=self.scope["user"].pk,
                is_active=True,
            )
            .first()
        )
        if context is None:
            raise PermissionError("No active campaign context.")
        return context

    @staticmethod
    def _incomplete_level_ups(campaign) -> list[dict[str, object]]:
        return [
            {
                "character_id": row.character_id,
                "character_name": row.character.name,
                "level": row.level,
            }
            for row in CharacterLevelProgress.objects.filter(
                character__campaign=campaign,
                character__is_active=True,
                character__is_archived=False,
                is_complete=False,
            ).select_related("character")
        ]

    @staticmethod
    def _invitation_data(invitation: CampaignInvitation) -> dict[str, object]:
        status = "pending"
        if invitation.accepted_at:
            status = "accepted"
        elif invitation.revoked_at:
            status = "revoked"
        elif invitation.expires_at <= timezone.now():
            status = "expired"
        return {
            "id": invitation.pk,
            "email": invitation.delivery_email,
            "created_at": invitation.created_at.isoformat(),
            "expires_at": invitation.expires_at.isoformat(),
            "accepted_at": invitation.accepted_at.isoformat()
            if invitation.accepted_at
            else None,
            "status": status,
        }

    def _invite_link(self, token: str) -> str:
        headers = dict(self.scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode().rstrip("/")
        return f"{origin}/invites/{token}" if origin else f"/invites/{token}"

    @staticmethod
    def _enabled_builder_entry(context, entry_id, kind: str):
        entry = CompendiumEntry.objects.filter(
            pk=entry_id,
            kind=kind,
            source__in=context.campaign.compendium_sources.all(),
        ).first()
        if entry is None:
            raise ValidationError(f"Selected {kind} is not enabled for this campaign.")
        return entry

    @staticmethod
    def _class_summary(character: Character) -> str:
        counts: dict[str, int] = {}
        for row in character.class_levels.all():
            counts[row.class_name] = counts.get(row.class_name, 0) + 1
        return " / ".join(f"{name} {level}" for name, level in counts.items())

    @staticmethod
    def _event_metadata(event) -> dict[str, object]:
        actor = None
        if event.created_by_id:
            actor = event.created_by.user.get_username()
        elif event.actor_username:
            actor = event.actor_username
        return {
            "occurred_at": event.occurred_at.isoformat(),
            "campaign_date": event.campaign_date,
            "actor": actor,
        }

    @classmethod
    def _health_data(cls, event: HealthTransaction) -> dict[str, object]:
        return {
            "id": event.pk,
            "ledger": "health",
            "ledger_label": str(event._meta.verbose_name),
            "character_id": event.character_id,
            "character_name": event.character.name,
            "reason": event.reason,
            "description": event.description,
            "current_hp_delta": event.current_hp_delta,
            "temporary_hp_delta": event.temporary_hp_delta,
            "current_hp_before": event.current_hp_before,
            "current_hp_after": event.current_hp_after,
            "temporary_hp_before": event.temporary_hp_before,
            "temporary_hp_after": event.temporary_hp_after,
            "entries": [],
            **cls._event_metadata(event),
        }

    @classmethod
    def _character_history_data(cls, event: CharacterHistory) -> dict[str, object]:
        return {
            "id": event.pk,
            "ledger": "character",
            "ledger_label": str(event._meta.verbose_name),
            "character_id": event.character_id,
            "character_name": event.character.name,
            "reason": event.reason,
            "description": event.description,
            "changes": event.changes,
            "entries": [],
            **cls._event_metadata(event),
        }

    @classmethod
    def _audit_data(cls, event) -> dict[str, object]:
        description = str(event._meta.verbose_name)
        changes: dict[str, object] = {}
        if isinstance(event, CampaignLevelEvent):
            changes = {
                "level": {
                    "before": event.previous_level,
                    "after": event.next_level,
                }
            }
        elif isinstance(event, MembershipEvent):
            changes = {"membership": {"before": event.before, "after": event.after}}
            description = event.get_reason_display()
        elif isinstance(event, InvitationEvent):
            description = event.get_reason_display()
        return {
            "id": event.pk,
            "ledger": f"audit.{event._meta.model_name}",
            "ledger_label": str(event._meta.verbose_name),
            "reason": getattr(event, "reason", event._meta.model_name),
            "description": description,
            "changes": changes,
            "entries": [],
            **cls._event_metadata(event),
        }

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


class UserConsumer(HoardJsonWebsocketConsumer):
    channel_layer_alias = "local"

    async def connect(self) -> None:
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        await self.accept()

    async def receive_json(self, content: dict[str, object], **kwargs: object) -> None:
        request_id = content.get("request_id")
        message_type = content.get("type")
        kind = operation_kind(message_type) if isinstance(message_type, str) else None
        if not is_uuid7(request_id):
            await self.send_json(
                {
                    "type": error_type(kind or operation_kind("")),
                    **({"request_id": request_id} if isinstance(request_id, str) else {}),
                    "code": "invalid_request_id",
                    "detail": "request_id must be a UUIDv7.",
                }
            )
            return
        if message_type != "user.contexts.list":
            await self.send_json(
                {
                    "type": error_type(operation_kind("")),
                    "request_id": request_id,
                    "code": "unsupported_message",
                    "detail": "Unsupported message.",
                }
            )
            return
        data = await self._contexts()
        await self.send_json(
            {"type": result_type(operation_kind(message_type)), "request_id": request_id, "data": data}
        )

    @database_sync_to_async
    def _contexts(self) -> list[dict[str, object]]:
        from .api import _context_data

        return [
            _context_data(context)
            for context in CampaignContext.objects.filter(
                user=self.scope["user"], is_active=True
            ).select_related("campaign", "character")
        ]


class InviteConsumer(HoardJsonWebsocketConsumer):
    channel_layer_alias = "local"

    async def connect(self) -> None:
        self.token = self.scope["url_route"]["kwargs"]["token"]
        if not await self._valid_token():
            await self.close(code=4404)
            return
        await self.accept()

    async def receive_json(self, content: dict[str, object], **kwargs: object) -> None:
        request_id = content.get("request_id")
        message_type = content.get("type")
        kind = operation_kind(message_type) if isinstance(message_type, str) else None
        if not is_uuid7(request_id):
            await self.send_json(
                {
                    "type": error_type(kind or operation_kind("")),
                    **({"request_id": request_id} if isinstance(request_id, str) else {}),
                    "code": "invalid_request_id",
                    "detail": "request_id must be a UUIDv7.",
                }
            )
            return
        handlers = {
            "invite.inspect": self._inspect,
            "invite.accept": self._accept,
            "invite.register_and_accept": self._register,
        }
        handler = handlers.get(content.get("type"))
        if handler is None:
            await self.send_json(
                {
                    "type": error_type(operation_kind("")),
                    "request_id": request_id,
                    "code": "unsupported_message",
                    "detail": "Unsupported message.",
                }
            )
            return
        try:
            data = await handler(content)
        except (ValidationError, ValueError, PermissionError) as error:
            field_errors = getattr(error, "message_dict", None)
            detail = field_errors or getattr(error, "messages", None) or str(error)
            code = (
                "forbidden"
                if isinstance(error, PermissionError)
                else "validation_error"
            )
            await self.send_json(
                {
                    "type": error_type(operation_kind(message_type)),
                    "request_id": request_id,
                    "code": code,
                    "detail": detail,
                    "field_errors": field_errors,
                }
            )
            return
        await self.send_json(
            {
                "type": result_type(operation_kind(message_type)),
                "request_id": request_id,
                "data": data,
            }
        )

    @database_sync_to_async
    def _valid_token(self) -> bool:
        from .services.invitations import invitation_for_token

        try:
            invitation_for_token(self.token)
        except ValidationError:
            return False
        return True

    @database_sync_to_async
    def _inspect(self, content: dict[str, object]) -> dict[str, object]:
        from .services.invitations import invitation_for_token

        invitation = invitation_for_token(self.token)
        return {
            "campaign_name": invitation.campaign.name,
            "expires_at": invitation.expires_at.isoformat(),
            "authenticated": self.scope["user"].is_authenticated,
            "username": self.scope["user"].get_username()
            if self.scope["user"].is_authenticated
            else None,
        }

    @database_sync_to_async
    def _accept(self, content: dict[str, object]) -> dict[str, object]:
        if not self.scope["user"].is_authenticated:
            raise PermissionError("Sign in before accepting this invitation.")
        context = accept_invitation(self.token, self.scope["user"])
        notify_campaign_changed(context.campaign_id)
        return {"context_id": context.pk, "character_id": context.character.pk}

    @database_sync_to_async
    def _register(self, content: dict[str, object]) -> dict[str, object]:
        username = str(content.get("username") or "").strip()
        email = str(content.get("email") or "").strip()
        password = str(content.get("password") or "")
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required.")
        validate_password(password)
        user, context = register_and_accept(self.token, username, email, password)
        notify_campaign_changed(context.campaign_id)
        return {
            "user_id": user.pk,
            "username": user.get_username(),
            "context_id": context.pk,
            "character_id": context.character.pk,
        }
