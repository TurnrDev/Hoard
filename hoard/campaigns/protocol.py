"""The transport-neutral WebSocket request protocol.

Operation names are deliberately classified here rather than guessed from their
spelling by a consumer.  This gives the REST compatibility layer and future
WebSocket consumers one protocol definition to share while the domain slices
are migrated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class OperationKind(StrEnum):
    QUERY = "query"
    COMMAND = "command"


class WebSocketContract(BaseModel):
    """Base class for JSON-safe WebSocket protocol contracts."""

    model_config = ConfigDict(extra="forbid")


class RequestEnvelope(WebSocketContract):
    """A client request correlated by a UUIDv7 identifier."""

    type: str
    request_id: str

    @field_validator("request_id")
    @classmethod
    def require_uuid7(cls, value: str) -> str:
        """Reject non-compliant request identifiers at the transport boundary."""
        if not is_uuid7(value):
            raise ValueError("request_id must be a UUIDv7.")

        return value


class QueryResultEnvelope(WebSocketContract):
    """A successful current-state query response."""

    type: str = "query.result"
    request_id: str
    data: Any


class CommandAcknowledgementEnvelope(WebSocketContract):
    """A successful synchronous command acknowledgement."""

    type: str = "command.ack"
    request_id: str


class RequestErrorEnvelope(WebSocketContract):
    """A correlated query or command failure."""

    type: str
    request_id: str | None = None
    code: str
    detail: Any
    field_errors: Mapping[str, Any] | None = None


class DomainEvent(WebSocketContract):
    """Base contract for an authorised server-initiated domain event."""

    type: str
    request_id: str | None = None


class EmptyPayload(WebSocketContract):
    """Contract for operations that accept no fields beyond the envelope."""


class FlexiblePayload(WebSocketContract):
    """Temporary Pydantic boundary for legacy operation-specific fields."""

    model_config = ConfigDict(extra="allow")


@dataclass(frozen=True)
class OperationDefinition:
    """The transport contract registered for a WebSocket operation."""

    name: str
    kind: OperationKind
    payload_model: type[WebSocketContract] = FlexiblePayload
    result_model: type[WebSocketContract] | None = None


QUERY_OPERATIONS = frozenset(
    {
        "campaign.get",
        "campaign.calendar.get",
        "campaign.members.list",
        "campaign.invites.list",
        "campaign.level.status",
        "characters.list",
        "characters.get",
        "characters.builder.definition",
        "characters.builder.entry.get",
        "characters.builder.get",
        "characters.level_up.definition",
        "characters.level_up.class.get",
        "characters.level_up.preview",
        "characters.level_up.feats",
        "characters.imports.cah.preview",
        "transactions.list",
        "compendium.items.list",
        "compendium.search",
        "compendium.sources.list",
        "compendium.repositories.list",
        "user.contexts.list",
        "invite.inspect",
    }
)

COMMAND_OPERATIONS = frozenset(
    {
        "campaign.calendar.adjust",
        "campaign.members.deactivate",
        "campaign.invites.create",
        "campaign.invites.resend",
        "campaign.invites.revoke",
        "campaign.level.approve",
        "campaign.presence.heartbeat",
        "campaign.encounter.start",
        "campaign.encounter.end",
        "campaign.encounter.combatants.add_character",
        "campaign.encounter.combatants.add",
        "campaign.encounter.combatants.reorder",
        "campaign.encounter.combatants.update",
        "campaign.encounter.combatants.remove",
        "campaign.encounter.current.set",
        "campaign.encounter.initiative.roll",
        "campaign.encounter.initiative.tie.choose",
        "campaign.encounter.turn.end",
        "campaign.encounter.conditions.set",
        "campaign.encounter.conditions.remove",
        "characters.conditions.set",
        "characters.conditions.remove",
        "characters.create",
        "characters.update",
        "characters.portrait.remove",
        "characters.archive",
        "characters.builder.save",
        "characters.builder.complete",
        "characters.level_up.complete",
        "characters.health.post",
        "characters.notes.create",
        "characters.notes.update",
        "characters.notes.delete",
        "characters.features.create",
        "characters.features.update",
        "characters.features.delete",
        "characters.spells.create",
        "characters.spells.delete",
        "characters.loadout.create",
        "characters.loadout.update",
        "characters.loadout.delete",
        "characters.effects.create",
        "characters.effects.update",
        "characters.effects.delete",
        "characters.spells.cast",
        "characters.rest",
        "characters.inspiration.set",
        "characters.companions.create",
        "characters.companions.update",
        "characters.companions.delete",
        "characters.imports.cah.begin",
        "characters.imports.cah.commit",
        "characters.imports.cah.cancel",
        "inventory.transactions.create",
        "money.transfers.create",
        "money.exchanges.create",
        "experience.shared_awards.create",
        "transactions.reverse",
        "compendium.items.create",
        "compendium.items.update",
        "compendium.items.delete",
        "compendium.spells.create",
        "compendium.spells.clone",
        "compendium.spells.update",
        "compendium.sources.enable",
        "compendium.sources.disable",
        "compendium.repositories.import",
        "invite.accept",
        "invite.register_and_accept",
    }
)


def operation_definitions() -> dict[str, OperationDefinition]:
    """Return the registered contracts for every currently supported operation."""
    from .payloads import (
        CalendarAdjustmentCommand,
        CampaignCalendarData,
        CharacterConditionCommand,
        CharacterConditionIdentifierCommand,
        CharacterCreateCommand,
        CharacterHealthCommand,
        CharacterIdentifierCommand,
        CharacterUpdateCommand,
        CombatantConditionCommand,
        CombatantConditionIdentifierCommand,
        EncounterCharacterAddCommand,
        EncounterCombatantAddCommand,
        EncounterCombatantIdentifierCommand,
        EncounterCombatantReorderCommand,
        EncounterCombatantUpdateCommand,
        EncounterCurrentCombatantCommand,
        InitiativeTieChoiceCommand,
        InvitationCreateCommand,
        InvitationIdentifierCommand,
        MemberDeactivationCommand,
        PlayerInitiativeRollCommand,
    )

    definitions = {
        name: OperationDefinition(name=name, kind=OperationKind.QUERY)
        for name in QUERY_OPERATIONS
    }
    definitions.update(
        {
            name: OperationDefinition(name=name, kind=OperationKind.COMMAND)
            for name in COMMAND_OPERATIONS
        }
    )
    definitions["campaign.calendar.get"] = OperationDefinition(
        name="campaign.calendar.get",
        kind=OperationKind.QUERY,
        payload_model=EmptyPayload,
        result_model=CampaignCalendarData,
    )
    definitions["campaign.calendar.adjust"] = OperationDefinition(
        name="campaign.calendar.adjust",
        kind=OperationKind.COMMAND,
        payload_model=CalendarAdjustmentCommand,
        result_model=CampaignCalendarData,
    )
    for name in ("campaign.encounter.start", "campaign.encounter.end"):
        definitions[name] = OperationDefinition(
            name=name,
            kind=OperationKind.COMMAND,
            payload_model=EmptyPayload,
        )
    definitions["campaign.encounter.combatants.add_character"] = OperationDefinition(
        name="campaign.encounter.combatants.add_character",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCharacterAddCommand,
    )
    definitions["campaign.encounter.combatants.add"] = OperationDefinition(
        name="campaign.encounter.combatants.add",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCombatantAddCommand,
    )
    definitions["campaign.encounter.combatants.update"] = OperationDefinition(
        name="campaign.encounter.combatants.update",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCombatantUpdateCommand,
    )
    definitions["campaign.encounter.combatants.reorder"] = OperationDefinition(
        name="campaign.encounter.combatants.reorder",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCombatantReorderCommand,
    )
    definitions["campaign.encounter.combatants.remove"] = OperationDefinition(
        name="campaign.encounter.combatants.remove",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCombatantIdentifierCommand,
    )
    definitions["campaign.encounter.current.set"] = OperationDefinition(
        name="campaign.encounter.current.set",
        kind=OperationKind.COMMAND,
        payload_model=EncounterCurrentCombatantCommand,
    )
    definitions["campaign.encounter.initiative.roll"] = OperationDefinition(
        name="campaign.encounter.initiative.roll",
        kind=OperationKind.COMMAND,
        payload_model=PlayerInitiativeRollCommand,
    )
    definitions["campaign.encounter.initiative.tie.choose"] = OperationDefinition(
        name="campaign.encounter.initiative.tie.choose",
        kind=OperationKind.COMMAND,
        payload_model=InitiativeTieChoiceCommand,
    )
    definitions["campaign.encounter.turn.end"] = OperationDefinition(
        name="campaign.encounter.turn.end",
        kind=OperationKind.COMMAND,
        payload_model=EmptyPayload,
    )
    definitions["campaign.encounter.conditions.set"] = OperationDefinition(
        name="campaign.encounter.conditions.set",
        kind=OperationKind.COMMAND,
        payload_model=CombatantConditionCommand,
    )
    definitions["campaign.encounter.conditions.remove"] = OperationDefinition(
        name="campaign.encounter.conditions.remove",
        kind=OperationKind.COMMAND,
        payload_model=CombatantConditionIdentifierCommand,
    )
    definitions["characters.conditions.set"] = OperationDefinition(
        name="characters.conditions.set",
        kind=OperationKind.COMMAND,
        payload_model=CharacterConditionCommand,
    )
    definitions["characters.conditions.remove"] = OperationDefinition(
        name="characters.conditions.remove",
        kind=OperationKind.COMMAND,
        payload_model=CharacterConditionIdentifierCommand,
    )
    definitions["campaign.members.deactivate"] = OperationDefinition(
        name="campaign.members.deactivate",
        kind=OperationKind.COMMAND,
        payload_model=MemberDeactivationCommand,
    )
    definitions["characters.health.post"] = OperationDefinition(
        name="characters.health.post",
        kind=OperationKind.COMMAND,
        payload_model=CharacterHealthCommand,
    )
    definitions["characters.create"] = OperationDefinition(
        name="characters.create",
        kind=OperationKind.COMMAND,
        payload_model=CharacterCreateCommand,
    )
    definitions["characters.update"] = OperationDefinition(
        name="characters.update",
        kind=OperationKind.COMMAND,
        payload_model=CharacterUpdateCommand,
    )
    definitions["characters.portrait.remove"] = OperationDefinition(
        name="characters.portrait.remove",
        kind=OperationKind.COMMAND,
        payload_model=CharacterIdentifierCommand,
    )
    definitions["characters.archive"] = OperationDefinition(
        name="characters.archive",
        kind=OperationKind.COMMAND,
        payload_model=CharacterIdentifierCommand,
    )
    definitions["campaign.invites.create"] = OperationDefinition(
        name="campaign.invites.create",
        kind=OperationKind.COMMAND,
        payload_model=InvitationCreateCommand,
    )
    for name in (
        "campaign.invites.resend",
        "campaign.invites.revoke",
    ):
        definitions[name] = OperationDefinition(
            name=name,
            kind=OperationKind.COMMAND,
            payload_model=InvitationIdentifierCommand,
        )

    return definitions


def operation_definition(operation: str) -> OperationDefinition:
    """Return the registered protocol definition for an operation."""
    return operation_definitions().get(
        operation,
        OperationDefinition(name=operation, kind=OperationKind.COMMAND),
    )


def operation_kind(operation: str) -> OperationKind:
    """Return the explicitly registered interaction kind for an operation."""
    return operation_definition(operation).kind


def is_uuid7(value: object) -> bool:
    """Return whether *value* is an RFC 9562 UUIDv7 request identifier."""
    if not isinstance(value, str):
        return False
    try:
        return UUID(value).version == 7
    except ValueError:
        return False


def result_type(kind: OperationKind) -> str:
    return "query.result" if kind == OperationKind.QUERY else "command.ack"


def error_type(kind: OperationKind) -> str:
    return "query.error" if kind == OperationKind.QUERY else "command.error"
