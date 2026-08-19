"""Typed import boundary for the supported 5e Companion CAH subset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from django.core.exceptions import ValidationError
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
)
from pydantic import (
    ValidationError as PydanticError,
)

ABILITIES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

SKILL_NAMES = (
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
)

CAH_PROFICIENCY = {
    "NONE": "none",
    "HALF": "half",
    "FULL": "proficient",
    "EXPERT": "expertise",
}


def _optional_integer(value: object) -> int | None:
    return value if type(value) is int else None


OptionalInteger = Annotated[
    int | None, BeforeValidator(_optional_integer), Field(default=None)
]


@dataclass(frozen=True)
class CahPreview:
    fields: dict[str, Any]
    warnings: list[str]


class CahModel(BaseModel):
    """Ignore the rest of a CAH export deliberately, rather than accidentally."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class CahRace(CahModel):
    race_id: str | None = Field(default=None, validation_alias="raceId")
    subrace_id: str | None = Field(default=None, validation_alias="subraceId")


class CahRequiredRace(CahModel):
    name: str | None = None


class CahAbility(CahModel):
    score: OptionalInteger = None
    score_modifier: OptionalInteger = Field(validation_alias="scoreModifier")
    save: bool | None = None
    save_modifier: OptionalInteger = Field(validation_alias="saveModifier")


class CahSkill(CahModel):
    name: str | None = Field(default=None, validation_alias="typeName")
    proficiency: str | None = Field(default=None, validation_alias="proficiencyName")


class CahCharacter(CahModel):
    json_type: Literal["character"] = Field(validation_alias="jsonType")
    name: str | None = None
    race: CahRace | None = None
    required_race: CahRequiredRace | None = Field(
        default=None, validation_alias="requiredRace"
    )
    base_hp: OptionalInteger = Field(validation_alias="baseHp")
    proficiency_modifier: OptionalInteger = Field(
        validation_alias="proficiencyModifier"
    )
    strength: CahAbility | None = None
    dexterity: CahAbility | None = None
    constitution: CahAbility | None = None
    intelligence: CahAbility | None = None
    wisdom: CahAbility | None = None
    charisma: CahAbility | None = None
    skills: list[CahSkill] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("required_race", mode="before")
    @classmethod
    def parse_required_race(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value


def _value(
    value: int | None, label: str, warnings: list[str], *, minimum: int | None = None
) -> int | None:
    if value is None:
        warnings.append(f"{label} was missing or invalid and was ignored.")
        return None
    if minimum is not None and value < minimum:
        warnings.append(f"{label} was below {minimum} and was ignored.")
        return None
    return value


def _set_number(
    fields: dict[str, Any],
    name: str,
    value: int | None,
    label: str,
    warnings: list[str],
    *,
    minimum: int | None = None,
) -> None:
    parsed = _value(value, label, warnings, minimum=minimum)
    if parsed is not None:
        fields[name] = parsed


def parse_cah(raw: bytes) -> CahPreview:
    """Return only stable reference-sheet fields, never raw CAH content."""

    try:
        source = CahCharacter.model_validate_json(raw)
    except PydanticError as error:
        raise ValidationError(
            "The uploaded file is not a valid 5e Companion character export."
        ) from error

    warnings: list[str] = []
    fields: dict[str, Any] = {"skill_proficiencies": {}}
    if source.name:
        fields["name"] = source.name
    else:
        warnings.append("Character name was missing and was not imported.")
    if source.required_race and source.required_race.name:
        fields["race"] = source.required_race.name
    elif source.race:
        race_name = source.race.subrace_id or source.race.race_id
        if race_name:
            fields["race"] = race_name.replace("_", " ").title()

    _set_number(fields, "base_hp", source.base_hp, "Base HP", warnings, minimum=1)
    _set_number(
        fields,
        "proficiency_bonus_adjustment",
        source.proficiency_modifier,
        "Proficiency adjustment",
        warnings,
    )

    for ability_name in ABILITIES:
        ability = getattr(source, ability_name)
        if ability is None:
            warnings.append(f"{ability_name.title()} was missing and was not imported.")
            continue
        _set_number(
            fields,
            ability_name,
            ability.score,
            f"{ability_name.title()} score",
            warnings,
            minimum=1,
        )
        _set_number(
            fields,
            f"{ability_name}_modifier_adjustment",
            ability.score_modifier,
            f"{ability_name.title()} adjustment",
            warnings,
        )
        _set_number(
            fields,
            f"{ability_name}_save_adjustment",
            ability.save_modifier,
            f"{ability_name.title()} save adjustment",
            warnings,
        )
        if ability.save is not None:
            fields[f"{ability_name}_save_proficient"] = ability.save

    for skill in source.skills:
        name = skill.name.lower() if skill.name else ""
        if name not in SKILL_NAMES:
            warnings.append(f"Unsupported skill {skill.name!r} was ignored.")
        elif skill.proficiency not in CAH_PROFICIENCY:
            warnings.append(f"Unknown proficiency for {name} was ignored.")
        else:
            fields["skill_proficiencies"][name] = CAH_PROFICIENCY[skill.proficiency]

    warnings.append(
        "AC, current/temporary HP, coins, XP, equipment, spells, feats, and notes were not imported."
    )
    return CahPreview(fields=fields, warnings=warnings)
