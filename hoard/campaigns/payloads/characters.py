"""Character command and event contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class NpcCharacterFields(BaseModel):
    """The supported fields for a GM-created NPC."""

    name: str
    race: str = ""
    character_class: str = ""
    is_npc: Literal[True]


class CharacterCreateCommand(BaseModel):
    """Validated input for creating an NPC in the active campaign."""

    fields: NpcCharacterFields


class CharacterIdentifierCommand(BaseModel):
    """Validated input for commands that address one character."""

    character_id: int = Field(gt=0)


class CharacterUpdateCommand(CharacterIdentifierCommand):
    """Validated envelope for an editable character field set."""

    fields: dict[str, object]


class CharacterLifecycleData(BaseModel):
    """Authoritative lifecycle fields shared by character list consumers."""

    id: int
    name: str
    is_active: bool


class CharacterLifecycleEvent(BaseModel):
    """Authoritative character lifecycle state after a lifecycle command."""

    type: Literal["character.created", "character.updated", "character.archived"]
    character: CharacterLifecycleData
    request_id: str | None = None
