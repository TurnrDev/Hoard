from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class EncounterCombatantIdentifierCommand(BaseModel):
    combatant_id: int = Field(gt=0)


class EncounterCurrentCombatantCommand(BaseModel):
    combatant_id: int | None = Field(default=None, gt=0)


class PlayerInitiativeRollCommand(BaseModel):
    roll: int = Field(ge=1, le=20)


class InitiativeTieChoiceCommand(BaseModel):
    combatant_id: int = Field(gt=0)


class EncounterCharacterAddCommand(BaseModel):
    character_id: int = Field(gt=0)
    initiative: int = Field(default=0, ge=-100, le=100)


class EncounterCombatantAddCommand(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    initiative: int = Field(default=0, ge=-100, le=100)
    current_hp: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_complete_health(self) -> EncounterCombatantAddCommand:
        if (self.current_hp is None) != (self.max_hp is None):
            raise ValueError("Current and maximum HP must be supplied together.")
        if not self.name.strip():
            raise ValueError("An encounter-only combatant requires a name.")

        return self


class EncounterCombatantUpdateCommand(EncounterCombatantIdentifierCommand):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    initiative: int | None = Field(default=None, ge=-100, le=100)
    current_hp: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)


class EncounterCombatantReorderCommand(BaseModel):
    combatant_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_combatants(self) -> EncounterCombatantReorderCommand:
        if len(self.combatant_ids) != len(set(self.combatant_ids)):
            raise ValueError("Combatant order cannot contain duplicates.")

        return self
