"""Defensive reader for legacy 5e Companion character exports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError

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


@dataclass(frozen=True)
class CahPreview:
    fields: dict[str, Any]
    collections: dict[str, list[dict[str, Any]]]
    inventory: list[dict[str, Any]]
    warnings: list[str]


def _json(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _dict(value: object) -> dict[str, Any]:
    value = _json(value)
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    value = _json(value)
    return value if isinstance(value, list) else []


def _integer(value: object, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
    except TypeError, ValueError:
        return None
    return result if minimum is None or result >= minimum else None


def _name(value: object) -> str:
    return str(value).replace("_", " ").title() if value else ""


def _description(value: object) -> str:
    if isinstance(value, str):
        return value
    model = _dict(value)
    if isinstance(model.get("description"), str):
        return model["description"]
    for row in _list(model.get("descriptionModels")):
        description = _dict(row).get("description")
        if isinstance(description, str):
            return description
    return ""


def _entry(value: object, *, kind: str = "item") -> dict[str, Any] | None:
    row = _dict(value)
    name = row.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return {
        "source_identifier": str(row.get("id") or ""),
        "name": name.strip(),
        "description": _description(row),
        "notes": row.get("notes") if isinstance(row.get("notes"), str) else "",
        "level": _integer(row.get("level"), minimum=0) or 0,
        "kind": kind,
        "raw": row,
    }


def _feature_entries(source: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for value in _list(source.get("feats")):
        entry = _entry(value, kind="feat")
        if entry:
            entries.append(entry)
    for value in _list(source.get("selectableFeatures")):
        row = _dict(value)
        for selected in _list(row.get("selectedFeatures")):
            entry = _entry(_dict(selected).get("feat", selected), kind="feature")
            if entry:
                entries.append(entry)
    return entries


def _inventory_entries(source: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for key, kind in (
        ("equipment", "item"),
        ("weapons", "weapon"),
        ("armors", "armor"),
    ):
        for index, value in enumerate(_list(source.get(key))):
            entry = _entry(value, kind=kind)
            if not entry:
                continue
            entry.update(
                line_id=f"{key}-{index}",
                quantity=_integer(_dict(value).get("amount"), minimum=1) or 1,
                equipped=bool(_dict(value).get("isEquipped")),
                action="add",
            )
            entries.append(entry)
    return entries


def _languages(*sources: dict[str, Any]) -> list[str]:
    """Keep Companion language instructions (for example, ``Choose 1``) intact."""
    values: list[str] = []
    for source in sources:
        for value in _list(source.get("languages")):
            row = _dict(value)
            label = row.get("proficiency") or row.get("name") or value
            if isinstance(label, str) and label.strip():
                values.append(label.strip())
    return list(dict.fromkeys(values))


def parse_cah(raw: bytes) -> CahPreview:
    """Parse supported sheet content while retaining import trace data per entry."""
    try:
        source = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("The uploaded file is not valid JSON.") from error
    if not isinstance(source, dict) or source.get("jsonType") != "character":
        raise ValidationError(
            "The uploaded file is not a 5e Companion character export."
        )

    warnings: list[str] = []
    fields: dict[str, Any] = {"skill_proficiencies": {}}
    if isinstance(source.get("name"), str) and source["name"].strip():
        fields["name"] = source["name"].strip()
    for target, source_key, minimum in (
        ("base_hp", "baseHp", 1),
        ("current_hp", "hp", None),
        ("temporary_hp", "tempHp", 0),
        ("base_ac", "baseAc", 1),
        ("ac_adjustment", "extraAC", None),
        ("proficiency_bonus_adjustment", "proficiencyModifier", None),
    ):
        value = _integer(source.get(source_key), minimum=minimum)
        if value is not None:
            fields[target] = value
    speed = source.get("speed")
    if isinstance(speed, str) and speed.strip():
        fields["speed"] = speed.strip()

    required_race = _dict(source.get("requiredRace"))
    race = (
        required_race.get("name")
        or _dict(source.get("race")).get("subraceId")
        or _dict(source.get("race")).get("raceId")
    )
    if race:
        fields["race"] = _name(race)
    required_background = _dict(source.get("requiredBackground"))
    background = required_background.get("name") or _dict(source.get("background")).get(
        "backgroundId"
    )
    if background:
        fields["background"] = _name(background)
    languages = _languages(required_race, required_background)
    if languages:
        fields["languages"] = languages
    jobs = _list(source.get("jobs"))
    if jobs and _dict(jobs[0]).get("jobId"):
        fields["character_class"] = _name(_dict(jobs[0])["jobId"])

    for ability_name in ABILITIES:
        ability = _dict(source.get(ability_name))
        if not ability:
            continue
        for suffix, key, minimum in (
            ("", "score", 1),
            ("_modifier_adjustment", "scoreModifier", None),
            ("_save_adjustment", "saveModifier", None),
        ):
            value = _integer(ability.get(key), minimum=minimum)
            if value is not None:
                fields[f"{ability_name}{suffix}"] = value
        if isinstance(ability.get("save"), bool):
            fields[f"{ability_name}_save_proficient"] = ability["save"]
    for value in _list(source.get("skills")):
        skill = _dict(value)
        name = str(skill.get("typeName") or "").lower().replace(" ", "_")
        proficiency = CAH_PROFICIENCY.get(str(skill.get("proficiencyName") or ""))
        if name in SKILL_NAMES and proficiency:
            fields["skill_proficiencies"][name] = proficiency

    notes = []
    about = source.get("about")
    if isinstance(about, str) and about.strip():
        notes.append({"title": "About", "body": about, "raw": {"about": about}})
    for note in _list(source.get("notes")):
        row = _dict(note)
        body = row.get("text")
        if isinstance(body, str) and body.strip():
            notes.append({"title": "", "body": body, "raw": row})
    spells = [
        entry
        for value in _list(source.get("spells"))
        if (entry := _entry(value, kind="spell"))
    ]
    companions = [
        entry
        for value in _list(source.get("companions"))
        if (entry := _entry(value, kind="monster"))
    ]
    for entry in companions:
        row = entry["raw"]
        entry.update(
            armor_class=_integer(row.get("armorClass") or row.get("ac"), minimum=1)
            or 10,
            max_hp=_integer(
                row.get("maxHp") or row.get("baseHp") or row.get("hp"), minimum=1
            )
            or 1,
            current_hp=_integer(row.get("hp")) or 1,
            speed=str(row.get("speed") or ""),
            abilities={
                ability: _integer(_dict(row.get(ability)).get("score"))
                for ability in ABILITIES
            },
            attacks=_list(row.get("attacks")),
        )
    fields["spell_slot_current"] = {
        key: value
        for key, raw_value in _dict(source.get("spellSlots")).items()
        if (value := _integer(raw_value, minimum=0)) is not None
    }
    return CahPreview(
        fields=fields,
        collections={
            "notes": notes,
            "features": _feature_entries(source),
            "spells": spells,
            "companions": companions,
        },
        inventory=_inventory_entries(source),
        warnings=warnings,
    )
