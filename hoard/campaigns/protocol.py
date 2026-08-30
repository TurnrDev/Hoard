"""The transport-neutral WebSocket request protocol.

Operation names are deliberately classified here rather than guessed from their
spelling by a consumer.  This gives the REST compatibility layer and future
WebSocket consumers one protocol definition to share while the domain slices
are migrated.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class OperationKind(StrEnum):
    QUERY = "query"
    COMMAND = "command"


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


def operation_kind(operation: str) -> OperationKind:
    """Return the explicitly registered interaction kind for an operation."""
    return (
        OperationKind.QUERY
        if operation in QUERY_OPERATIONS
        else OperationKind.COMMAND
    )


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
