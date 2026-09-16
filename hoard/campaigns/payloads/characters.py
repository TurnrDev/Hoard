"""Character command and event contracts."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class CharacterHealthCommand(CharacterIdentifierCommand):
    reason: Literal["damage", "healing", "temporary", "correction"]
    current_hp_delta: int = 0
    temporary_hp_delta: int = 0
    current_hp: int | None = Field(default=None, ge=0)
    temporary_hp: int | None = Field(default=None, ge=0)
    description: str = ""

    @model_validator(mode="after")
    def require_correction_values(self):
        if self.reason == "correction":
            if self.current_hp is None and self.temporary_hp is None:
                raise ValueError("A correction must set current or temporary HP.")
        elif self.current_hp is not None or self.temporary_hp is not None:
            raise ValueError("Only corrections may set absolute HP values.")

        return self


class CharacterRestCommand(CharacterIdentifierCommand):
    kind: Literal["short", "long"]
    regained_hp: int = Field(default=0, ge=0)


class CharacterHealthChangedEvent(BaseModel):
    type: Literal["character.health_changed"] = "character.health_changed"
    character_id: int
    max_hp: int
    current_hp: int
    temporary_hp: int
    request_id: str | None = None


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
