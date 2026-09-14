from typing import Literal

from pydantic import BaseModel, Field, model_validator

ConditionIdentifier = Literal[
    "blinded",
    "charmed",
    "deafened",
    "exhaustion",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
    "pacify",
]


class EncounterCombatantIdentifierCommand(BaseModel):
    """A command addressing one combatant in the active encounter."""

    combatant_id: int = Field(gt=0)


class CharacterConditionIdentifierCommand(BaseModel):
    """A command removing one condition cause or every cause of one condition."""

    character_id: int = Field(gt=0)
    condition_id: int | None = Field(default=None, gt=0)
    identifier: ConditionIdentifier | None = None

    @model_validator(mode="after")
    def require_condition_reference(self) -> CharacterConditionIdentifierCommand:
        """Require an instance ID or a condition identifier, but not both."""
        if (self.condition_id is None) == (self.identifier is None):
            raise ValueError("Supply either condition_id or identifier.")

        return self


class CharacterConditionCommand(BaseModel):
    """Apply a condition cause or update one existing cause on a character."""

    character_id: int = Field(gt=0)
    condition_id: int | None = Field(default=None, gt=0)
    identifier: ConditionIdentifier
    source: str = Field(default="", max_length=200)
    duration: str = Field(default="", max_length=200)
    exhaustion_level: int | None = Field(default=None, ge=1, le=6)

    @model_validator(mode="after")
    def validate_exhaustion_level(self) -> CharacterConditionCommand:
        """Require a level only for exhaustion."""
        validate_condition_level(self.identifier, self.exhaustion_level)

        return self


class EncounterCharacterAddCommand(BaseModel):
    """Add a campaign character to the active encounter."""

    character_id: int = Field(gt=0)
    initiative: int = Field(default=0, ge=-100, le=100)


class EncounterCombatantAddCommand(BaseModel):
    """Add a Compendium-backed or encounter-only combatant."""

    name: str = Field(default="", max_length=200)
    creature_entry_id: int | None = Field(default=None, gt=0)
    initiative: int = Field(default=0, ge=-100, le=100)
    current_hp: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)
    show_hp_bar: bool = False
    show_hp_numbers: bool = False

    @model_validator(mode="after")
    def require_complete_health(self) -> EncounterCombatantAddCommand:
        """Require current and maximum HP together when health is tracked."""
        if (self.current_hp is None) != (self.max_hp is None):
            raise ValueError("Current and maximum HP must be supplied together.")
        if self.creature_entry_id is None and not self.name.strip():
            raise ValueError("An encounter-only combatant requires a name.")

        return self


class EncounterCombatantUpdateCommand(EncounterCombatantIdentifierCommand):
    """Update mutable initiative and display state for a combatant."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    initiative: int | None = Field(default=None, ge=-100, le=100)
    current_hp: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)
    show_hp_bar: bool | None = None
    show_hp_numbers: bool | None = None


class CombatantConditionCommand(EncounterCombatantIdentifierCommand):
    """Apply a condition cause or update one existing cause on a combatant."""

    condition_id: int | None = Field(default=None, gt=0)
    identifier: ConditionIdentifier
    source: str = Field(default="", max_length=200)
    duration: str = Field(default="", max_length=200)
    exhaustion_level: int | None = Field(default=None, ge=1, le=6)

    @model_validator(mode="after")
    def validate_exhaustion_level(self) -> CombatantConditionCommand:
        """Require a level only for exhaustion."""
        validate_condition_level(self.identifier, self.exhaustion_level)

        return self


class CombatantConditionIdentifierCommand(EncounterCombatantIdentifierCommand):
    """Remove one condition cause or every cause of one condition."""

    condition_id: int | None = Field(default=None, gt=0)
    identifier: ConditionIdentifier | None = None

    @model_validator(mode="after")
    def require_condition_reference(self) -> CombatantConditionIdentifierCommand:
        """Require an instance ID or a condition identifier, but not both."""
        if (self.condition_id is None) == (self.identifier is None):
            raise ValueError("Supply either condition_id or identifier.")

        return self


def validate_condition_level(
    identifier: ConditionIdentifier,
    exhaustion_level: int | None,
) -> None:
    """Validate the condition-specific exhaustion level contract."""
    if identifier == "exhaustion" and exhaustion_level is None:
        raise ValueError("Exhaustion requires a level from 1 to 6.")
    if identifier != "exhaustion" and exhaustion_level is not None:
        raise ValueError("Only exhaustion may have an exhaustion level.")
