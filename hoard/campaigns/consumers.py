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
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from ninja.errors import HttpError

from .models import (
    CampaignContext,
    CampaignInvitation,
    Character,
    InvitationEvent,
    MembershipEvent,
)
from .payloads import (
    CampaignCalendarChangedEvent,
    CampaignCalendarData,
    CampaignInvitationChangedEvent,
    CampaignInvitationData,
    CampaignMemberData,
    CampaignMembershipChangedEvent,
    CampaignPresenceChangedEvent,
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
    context_group_name,
    notify_campaign_changed,
    notify_campaign_event,
)
from .services import (
    CharacterLifecycleService,
    accept_invitation,
    create_invitation,
    register_and_accept,
)
from .services.calendar import CampaignCalendarService

logger = logging.getLogger(__name__)
MAX_WEBSOCKET_RESPONSE_BYTES = settings.DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE - 65_536


class HoardJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def encode_json(cls, content: object) -> str:
        return json.dumps(content, cls=DjangoJSONEncoder)


class ContextConsumer(HoardJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope["user"]
        context_id = int(self.scope["url_route"]["kwargs"]["context_id"])
        active_context_ids = (
            await self.active_context_ids(user.pk, context_id)
            if user.is_authenticated
            else None
        )
        if active_context_ids is None:
            await self.close(code=4403)
            return
        self.context_id, self.campaign_id = active_context_ids
        self.group_name = campaign_group_name(self.campaign_id)
        self.context_group_name = context_group_name(self.context_id)
        self.request_tasks: set[asyncio.Task[None]] = set()
        self.request_slots = asyncio.Semaphore(8)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(self.context_group_name, self.channel_name)
        await self.accept()
        await self.record_presence()
        await self.publish_presence(True)

    async def disconnect(self, close_code: int) -> None:
        for task in tuple(getattr(self, "request_tasks", ())):
            task.cancel()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "context_group_name"):
            await self.channel_layer.group_discard(
                self.context_group_name,
                self.channel_name,
            )
        if hasattr(self, "context_id"):
            await self.remove_presence()
            await self.publish_presence(False)

    async def publish_presence(self, connected: bool) -> None:
        event = CampaignPresenceChangedEvent(
            context_id=self.context_id,
            connected=connected,
            last_seen_at=timezone.now().isoformat() if connected else None,
        )
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "domain.event", "event": event.model_dump(mode="json")},
        )

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
                    **(
                        {"request_id": request_id}
                        if isinstance(request_id, str)
                        else {}
                    ),
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
            "campaign.presence.heartbeat": self._presence_heartbeat,
            "characters.list": self._character_list,
            "characters.get": self._character_get,
            "characters.create": self._character_create,
            "characters.update": self._character_update,
            "characters.portrait.remove": self._character_portrait_remove,
            "characters.archive": self._character_archive,
            "characters.health.post": self._character_health_adjust,
            "characters.rest": self._character_rest,
            "transactions.list": self._transaction_list,
            "money.transfers.create": self._money_transfer_create,
            "money.exchanges.create": self._money_exchange_create,
            "experience.shared_awards.create": self._shared_xp_create,
            "transactions.reverse": self._transaction_reverse,
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
        await self.send_json(
            {
                "type": "error",
                "request_id": request_id,
                "code": "unsupported_message",
                "detail": "Unsupported message.",
            }
        )
        return

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
            "campaign.presence.heartbeat",
            "characters.create",
            "characters.update",
            "characters.portrait.remove",
            "characters.archive",
            "characters.health.post",
            "characters.rest",
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
    def active_context_ids(
        self, user_id: int, context_id: int
    ) -> tuple[int, int] | None:
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
            character_data,
            context_data,
            encounter_data,
            party_money,
            visible_characters,
        )

        context = self._context()
        campaign = context.campaign
        connected_context_ids = self.connected_context_ids(campaign.pk)
        return {
            **context_data(context),
            "id": campaign.pk,
            "name": campaign.name,
            "is_game_master": context.kind == CampaignContext.Kind.GM,
            "shared_experience": campaign.shared_experience,
            "level": campaign.level,
            "eligible_level": Character.level_for_experience(
                campaign.shared_experience
            ),
            "calendar": CampaignCalendarData.from_campaign(campaign).model_dump(
                mode="json"
            ),
            "party_money": party_money(campaign),
            "encounter": encounter_data(campaign),
            "members": [
                {
                    "id": candidate.pk,
                    "username": candidate.user.get_username(),
                    "first_name": candidate.user.first_name,
                    "last_name": candidate.user.last_name,
                    "is_game_master": candidate.kind == CampaignContext.Kind.GM,
                    "is_active": candidate.is_active,
                    "connected": candidate.pk in connected_context_ids,
                    "last_seen_at": (
                        candidate.last_seen_at.isoformat()
                        if candidate.last_seen_at
                        else None
                    ),
                }
                for candidate in CampaignContext.objects.filter(
                    campaign=campaign
                ).select_related("user")
            ],
            "characters": [
                character_data(value, context) for value in visible_characters(context)
            ],
            "invitations": (
                [self._invitation_data(value) for value in campaign.invitations.all()]
                if context.kind == CampaignContext.Kind.GM
                else []
            ),
        }

    @database_sync_to_async
    def _calendar_get(self, content: dict[str, object]) -> dict[str, object]:
        return CampaignCalendarData.from_campaign(self._context().campaign).model_dump(
            mode="json"
        )

    @database_sync_to_async
    def _calendar_adjust(self, content: dict[str, object]) -> dict[str, object]:
        from .api import gm_context

        context = self._context()
        gm_context(context)
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
    def _presence_heartbeat(self, content: dict[str, object]) -> None:
        last_seen_at = timezone.now()
        CampaignContext.objects.filter(pk=self.context_id).update(
            last_seen_at=last_seen_at,
        )
        notify_campaign_event(
            self.campaign_id,
            CampaignPresenceChangedEvent(
                context_id=self.context_id,
                connected=True,
                last_seen_at=last_seen_at.isoformat(),
            ),
        )

    @database_sync_to_async
    def _member_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import gm_context

        context = self._context()
        gm_context(context)
        connected_context_ids = self.connected_context_ids(context.campaign_id)
        return [
            {
                "id": candidate.pk,
                "username": candidate.user.get_username(),
                "first_name": candidate.user.first_name,
                "last_name": candidate.user.last_name,
                "is_game_master": candidate.kind == CampaignContext.Kind.GM,
                "is_active": candidate.is_active,
                "connected": candidate.pk in connected_context_ids,
                "last_seen_at": (
                    candidate.last_seen_at.isoformat()
                    if candidate.last_seen_at
                    else None
                ),
            }
            for candidate in CampaignContext.objects.filter(
                campaign=context.campaign
            ).select_related("user")
        ]

    @database_sync_to_async
    def _member_deactivate(self, content: dict[str, object]) -> None:
        from .api import gm_context

        context = self._context()
        gm_context(context)
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
            character.save(update_fields=("is_active",))
        notify_campaign_event(
            context.campaign_id,
            CampaignMembershipChangedEvent(
                member=CampaignMemberData(
                    id=candidate.pk,
                    username=candidate.user.get_username(),
                    first_name=candidate.user.first_name,
                    last_name=candidate.user.last_name,
                    is_game_master=candidate.kind == CampaignContext.Kind.GM,
                    is_active=candidate.is_active,
                ),
                request_id=str(content["request_id"]),
            ),
        )

    @database_sync_to_async
    def _invite_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import gm_context

        context = self._context()
        gm_context(context)
        return [
            self._invitation_data(value) for value in context.campaign.invitations.all()
        ]

    @database_sync_to_async
    def _invite_create(self, content: dict[str, object]) -> dict[str, object]:
        from .api import gm_context

        context = self._context()
        gm_context(context)
        email = self._string(content, "email", maximum=254)
        invitation, token = create_invitation(context, email)
        link = self._invite_link(token)
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
        from .api import gm_context
        from .services.invitations import token_digest

        context = self._context()
        gm_context(context)
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
        from .api import gm_context

        context = self._context()
        gm_context(context)
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
    def _character_list(self, content: dict[str, object]) -> list[dict[str, object]]:
        from .api import character_data, visible_characters

        context = self._context()
        return [character_data(value, context) for value in visible_characters(context)]

    @database_sync_to_async
    def _character_get(self, content: dict[str, object]) -> dict[str, object]:
        from .api import character_data, character_for_context, visible_characters

        context = self._context()
        character = character_for_context(
            context, self._integer(content, "character_id")
        )
        if not visible_characters(context).filter(pk=character.pk).exists():
            raise HttpError(404, "Character not found.")
        return character_data(character, context)

    @database_sync_to_async
    def _character_create(self, content: dict[str, object]) -> dict[str, object]:
        from .api import character_data, gm_context

        context = self._context()
        gm_context(context)
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
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return character_data(character, context)

    @database_sync_to_async
    def _character_update(self, content: dict[str, object]) -> dict[str, object]:
        from .api import character_data, editable_character

        context = self._context()
        character = editable_character(context, self._integer(content, "character_id"))
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
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return character_data(character, context)

    @database_sync_to_async
    def _character_portrait_remove(
        self, content: dict[str, object]
    ) -> dict[str, object]:
        from .api import character_data, editable_character

        context = self._context()
        character = editable_character(context, self._integer(content, "character_id"))
        character.portrait.delete(save=True)
        notify_campaign_changed(context.campaign_id, str(content["request_id"]))

        return character_data(character, context)

    @database_sync_to_async
    def _character_archive(self, content: dict[str, object]) -> dict[str, object]:
        from .api import character_data, editable_character

        context = self._context()
        character = editable_character(context, self._integer(content, "character_id"))
        character = CharacterLifecycleService().archive(context, character)
        notify_campaign_event(
            context.campaign_id,
            CharacterLifecycleEvent(
                type="character.archived",
                character=CharacterLifecycleData(
                    id=character.pk,
                    name=character.name,
                    is_active=character.is_active,
                ),
                request_id=str(content["request_id"]),
            ),
        )
        return character_data(character, context)

    @database_sync_to_async
    def _character_health_adjust(self, content: dict[str, object]) -> None:
        from .api import editable_character
        from .payloads import CharacterHealthCommand
        from .services.health import adjust_health

        context = self._context()
        command = CharacterHealthCommand.model_validate(content)
        character = editable_character(context, command.character_id)
        amount = (
            -command.current_hp_delta
            if command.reason == "damage"
            else command.current_hp_delta
            if command.reason == "healing"
            else command.temporary_hp_delta
        )
        updated = adjust_health(
            character,
            reason=command.reason,
            amount=amount,
            current_hp=command.current_hp,
            temporary_hp=command.temporary_hp,
            description=command.description,
            created_by=context,
        )
        notify_campaign_event(
            context.campaign_id,
            CharacterHealthChangedEvent(
                character_id=updated.pk,
                max_hp=updated.max_hp,
                current_hp=updated.current_hp,
                temporary_hp=updated.temporary_hp,
                request_id=str(content["request_id"]),
            ),
        )

    @database_sync_to_async
    def _character_rest(self, content: dict[str, object]) -> None:
        from .api import editable_character
        from .payloads import CharacterRestCommand
        from .services.health import take_rest

        context = self._context()
        command = CharacterRestCommand.model_validate(content)
        character = editable_character(context, command.character_id)
        updated = take_rest(
            character,
            kind=command.kind,
            regained_hp=command.regained_hp,
            created_by=context,
        )
        notify_campaign_event(
            context.campaign_id,
            CharacterHealthChangedEvent(
                character_id=updated.pk,
                max_hp=updated.max_hp,
                current_hp=updated.current_hp,
                temporary_hp=updated.temporary_hp,
                request_id=str(content["request_id"]),
            ),
        )

    @database_sync_to_async
    def _transaction_list(self, content: dict[str, object]) -> dict[str, object]:
        from .api import TRANSACTION_MODELS, history_data, transaction_queryset

        context = self._context()
        ledger = self._string(content, "ledger") or "all"
        rows: list[dict[str, object]] = []
        if ledger in ("all", "money", "experience"):
            ledgers = ("money", "experience") if ledger == "all" else (ledger,)
            for ledger_name in ledgers:
                model = TRANSACTION_MODELS[ledger_name]
                query = transaction_queryset(model, context.campaign)
                if context.kind != CampaignContext.Kind.GM:
                    query = query.filter(
                        entries__account__character__context__user=context.user
                    ).distinct()
                rows.extend(history_data(posted) for posted in query)
        if ledger in ("all", "audit"):
            audit_models = []
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

    @database_sync_to_async
    def record_presence(self) -> None:
        CampaignContext.objects.filter(pk=self.context_id).update(
            last_seen_at=timezone.now(),
        )

    @database_sync_to_async
    def remove_presence(self) -> None:
        CampaignContext.objects.filter(pk=self.context_id).update(last_seen_at=None)

    @staticmethod
    def connected_context_ids(campaign_id: int) -> set[int]:
        cutoff = timezone.now() - timedelta(seconds=60)

        return set(
            CampaignContext.objects.filter(
                campaign_id=campaign_id,
                last_seen_at__gte=cutoff,
            ).values_list("pk", flat=True)
        )

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
    def _audit_data(cls, event) -> dict[str, object]:
        description = str(event._meta.verbose_name)
        changes: dict[str, object] = {}
        if isinstance(event, MembershipEvent):
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
                    **(
                        {"request_id": request_id}
                        if isinstance(request_id, str)
                        else {}
                    ),
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
            {
                "type": result_type(operation_kind(message_type)),
                "request_id": request_id,
                "data": data,
            }
        )

    @database_sync_to_async
    def _contexts(self) -> list[dict[str, object]]:
        from .api import context_data

        return [
            context_data(context)
            for context in CampaignContext.objects.filter(
                user=self.scope["user"], is_active=True
            ).select_related("campaign", "character")
        ]


class InviteConsumer(HoardJsonWebsocketConsumer):
    channel_layer_alias = "local"

    async def connect(self) -> None:
        self.token = self.scope["url_route"]["kwargs"]["token"]
        await self.accept()

    async def receive_json(self, content: dict[str, object], **kwargs: object) -> None:
        request_id = content.get("request_id")
        message_type = content.get("type")
        kind = operation_kind(message_type) if isinstance(message_type, str) else None
        if not is_uuid7(request_id):
            await self.send_json(
                {
                    "type": error_type(kind or operation_kind("")),
                    **(
                        {"request_id": request_id}
                        if isinstance(request_id, str)
                        else {}
                    ),
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
