from pydantic import Field

from .characters import CharacterIdentifierCommand


class DiceCloudLinkCommand(CharacterIdentifierCommand):
    creature: str = Field(min_length=8, max_length=500)


class CharacterActiveCommand(CharacterIdentifierCommand):
    is_active: bool
