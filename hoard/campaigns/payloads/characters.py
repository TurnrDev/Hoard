"""Character command and event contracts."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CharacterHealthCommand(BaseModel):
    """Validated input for recording a character health change."""

    character_id: int = Field(gt=0)
    reason: Literal["damage", "healing", "temporary", "correction"]
    current_hp_delta: int = 0
    temporary_hp_delta: int = 0
    current_hp: int | None = Field(default=None, ge=0)
    temporary_hp: int | None = Field(default=None, ge=0)
    description: str = ""

    @model_validator(mode="after")
    def require_correction_values(self) -> CharacterHealthCommand:
        """Require absolute values for corrections and forbid them otherwise."""
        if self.reason == "correction":
            if self.current_hp is None and self.temporary_hp is None:
                raise ValueError("A correction must set current or temporary HP.")
        elif self.current_hp is not None or self.temporary_hp is not None:
            raise ValueError("Only corrections may set absolute HP values.")

        return self


class CharacterHealthChangedEvent(BaseModel):
    """Authoritative health values after a successful health command."""

    type: Literal["character.health_changed"] = "character.health_changed"
    character_id: int
    current_hp: int
    temporary_hp: int
    request_id: str | None = None
