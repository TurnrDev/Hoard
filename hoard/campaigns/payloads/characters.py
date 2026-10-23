"""Character identifier contracts."""

from pydantic import BaseModel, Field


class CharacterIdentifierCommand(BaseModel):
    """Validated input for commands that address one character."""

    character_id: int = Field(gt=0)
