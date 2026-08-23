from __future__ import annotations

from typing import Any

from ..models import Character, CharacterHistory

TRACKED_CHARACTER_FIELDS = (
    "name",
    "race",
    "subrace_name",
    "character_class",
    "background",
    "alignment",
    "personality_traits",
    "ideals",
    "bonds",
    "flaws",
    "about",
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
    "ability_bonuses",
    "ability_score_adjustments",
    "base_hp",
    "hp_ability",
    "hp_adjustment",
    "base_ac",
    "ac_adjustment",
    "speed",
    "languages",
    "equipment_proficiencies",
    "skill_proficiencies",
    "is_active",
    "is_build_complete",
)


def character_snapshot(character: Character) -> dict[str, Any]:
    return {field: getattr(character, field) for field in TRACKED_CHARACTER_FIELDS}


def record_character_history(
    character: Character,
    *,
    reason: str,
    before: dict[str, Any] | None,
    created_by=None,
    description: str = "",
) -> CharacterHistory:
    after = character_snapshot(character)
    changes = {
        key: {"before": before.get(key) if before else None, "after": value}
        for key, value in after.items()
        if before is None or before.get(key) != value
    }
    return CharacterHistory.objects.create(
        campaign=character.campaign,
        character=character,
        created_by=created_by,
        reason=reason,
        description=description,
        changes=changes,
    )
