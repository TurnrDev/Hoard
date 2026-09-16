"""Transactional native runtime and one-way Hoard projection services."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When

from hoard.compendium.models import CompendiumEntry, CompendiumSource
from hoard.compendium.native.runtime import (
    SUPPORTED_NATIVE_VIEW_TYPES,
    NativeEvaluator,
    NativeExecution,
    NativeRuntime,
    NativeRuntimeError,
    NativeScope,
    assign_native_value,
    native_resource_identifier,
    native_resources,
)

from ..models import CampaignContext, Character, CharacterNativeEvent

ABILITY_IDS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)
HOARD_STATS = (
    {
        "id": "hoard_temporary_hp",
        "name": "Temporary HP",
        "type": "base",
        "value_type": "integer",
        "default_value": 0,
        "party_visible": True,
    },
    {
        "id": "hoard_inspiration",
        "name": "Inspiration",
        "type": "base",
        "value_type": "bool",
        "default_value": False,
    },
    {
        "id": "hoard_inspiration_expires_at",
        "name": "Inspiration expiry",
        "type": "base",
        "value_type": "string",
        "default_value": "",
    },
    {
        "id": "hoard_is_dead",
        "name": "Dead",
        "type": "base",
        "value_type": "bool",
        "default_value": False,
    },
    {
        "id": "hoard_died_campaign_era",
        "name": "Death campaign era",
        "type": "base",
        "value_type": "string",
        "default_value": "",
    },
    {
        "id": "hoard_died_campaign_year",
        "name": "Death campaign year",
        "type": "base",
        "value_type": "integer",
        "default_value": None,
    },
    {
        "id": "hoard_died_campaign_day",
        "name": "Death campaign day",
        "type": "base",
        "value_type": "integer",
        "default_value": None,
    },
    {
        "id": "hoard_group_experience",
        "name": "Group experience",
        "type": "base",
        "value_type": "integer",
        "default_value": 0,
        "party_visible": True,
    },
    *(
        {
            "id": f"hoard_{field}",
            "name": field.replace("_", " ").title(),
            "type": "base",
            "value_type": value_type,
            "default_value": deepcopy(default),
        }
        for field, value_type, default in (
            ("race", "string", ""),
            ("subrace_name", "string", ""),
            ("character_class", "string", ""),
            ("background", "string", ""),
            ("ability_bonuses", "map", {}),
            ("ability_score_adjustments", "map", {}),
            ("hp_ability", "string", "constitution"),
            ("hp_adjustment", "integer", 0),
            ("base_ac", "integer", 10),
            ("ac_adjustment", "integer", 0),
            ("speed", "string", ""),
            ("spell_slot_adjustments", "map", {}),
            ("proficiency_bonus_adjustment", "integer", 0),
            ("strength_modifier_adjustment", "integer", 0),
            ("dexterity_modifier_adjustment", "integer", 0),
            ("constitution_modifier_adjustment", "integer", 0),
            ("intelligence_modifier_adjustment", "integer", 0),
            ("wisdom_modifier_adjustment", "integer", 0),
            ("charisma_modifier_adjustment", "integer", 0),
            ("strength_save_proficient", "bool", False),
            ("dexterity_save_proficient", "bool", False),
            ("constitution_save_proficient", "bool", False),
            ("intelligence_save_proficient", "bool", False),
            ("wisdom_save_proficient", "bool", False),
            ("charisma_save_proficient", "bool", False),
            ("strength_save_adjustment", "integer", 0),
            ("dexterity_save_adjustment", "integer", 0),
            ("constitution_save_adjustment", "integer", 0),
            ("intelligence_save_adjustment", "integer", 0),
            ("wisdom_save_adjustment", "integer", 0),
            ("charisma_save_adjustment", "integer", 0),
        )
    ),
)

NATIVE_TEXT_FIELDS = (
    "name",
    "alignment",
    "personality_traits",
    "ideals",
    "bonds",
    "flaws",
    "about",
)
HOARD_PROJECTED_FIELDS = tuple(
    stat["id"].removeprefix("hoard_")
    for stat in HOARD_STATS
    if stat["id"].startswith("hoard_")
    and stat["id"]
    not in {
        "hoard_temporary_hp",
        "hoard_inspiration",
        "hoard_inspiration_expires_at",
        "hoard_group_experience",
    }
)

# Hoard renders these standard sheet areas with its own styled, accessible
# components. Native sections outside this set remain available through the
# generic RPG Companion view renderer.
HOARD_RENDERED_SHEET_SECTIONS = frozenset(
    {
        "avatar",
        "conditions",
        "status",
        "abilities",
        "saving_throws",
        "skills",
        "equipment",
        "armors",
        "weapons",
        "features",
        "notes",
        "spell_slots",
        "spells",
        "companions",
        "death_saving_throws",
        "attuned_items",
    }
)


@dataclass(frozen=True)
class NativeCommandResult:
    """Persisted native execution and its immutable audit record."""

    character: Character
    execution: NativeExecution
    event: CharacterNativeEvent


def character_native_source(character: Character) -> CompendiumSource:
    """Resolve the exact enabled system definition used by a character."""
    if character.native_system_source_id:
        source = character.native_system_source
        is_enabled = character.campaign.compendium_sources.filter(
            pk=character.native_system_source_id
        ).exists()
        if source is not None and source.system_definition and is_enabled:
            return source

    campaign_source = character.campaign.native_system_source
    if (
        campaign_source is not None
        and campaign_source.identifier == character.native_system_id
        and campaign_source.system_definition
    ):
        character.campaign.compendium_sources.add(campaign_source)
        return campaign_source

    sources = character.campaign.compendium_sources.filter(
        identifier=character.native_system_id,
    ).exclude(system_definition={})
    if character.native_system_version:
        sources = sources.filter(version=character.native_system_version)
    source = (
        sources.annotate(
            default_priority=Case(
                When(repository__identifier="default", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("default_priority", "repository__identifier")
        .first()
    )
    if source is None:
        source = (
            CompendiumSource.objects.filter(
                identifier=character.native_system_id,
                repository__identifier="default",
                repository__campaign__isnull=True,
            )
            .exclude(system_definition={})
            .order_by("repository_id")
            .first()
        )
    if source is None:
        raise ValidationError(
            f"No installed {character.native_system_id} native system is available."
        )
    character.campaign.compendium_sources.add(source)
    if character.campaign.native_system_source_id is None:
        character.campaign.native_system_source = source
        character.campaign.native_system_id = source.identifier
        character.campaign.save(
            update_fields=("native_system_source", "native_system_id")
        )
    return source


def hoard_native_definition(source: CompendiumSource) -> dict[str, Any]:
    """Return the upstream definition with namespaced Hoard projection stats."""
    definition = deepcopy(source.system_definition)
    stats = definition.setdefault("character_stats", [])
    identifiers = {
        stat.get("id") for stat in stats if isinstance(stat, dict)
    }
    stats.extend(deepcopy(stat) for stat in HOARD_STATS if stat["id"] not in identifiers)
    return definition


def initial_native_state(
    character: Character,
    definition: dict[str, Any],
) -> dict[str, Any]:
    """Create a native baseline from existing Hoard projections once."""
    evaluator = NativeEvaluator(definition, {})
    state = evaluator.default_state()
    state.update(
        {
            "name": character.name,
            "base_hp": character.base_hp,
            "current_hp": character.current_hp,
            "hoard_temporary_hp": character.temporary_hp,
            "hoard_inspiration": character.has_inspiration,
            "hoard_inspiration_expires_at": (
                character.inspiration_expires_at.isoformat()
                if character.inspiration_expires_at
                else ""
            ),
            "hoard_group_experience": character.campaign.shared_experience,
        }
    )
    for field in NATIVE_TEXT_FIELDS:
        state[field] = getattr(character, field)
    for field in HOARD_PROJECTED_FIELDS:
        state[f"hoard_{field}"] = deepcopy(getattr(character, field))
    state["language_proficiencies"] = deepcopy(character.languages)
    for category, stat in (
        ("armor", "armor_proficiencies"),
        ("weapons", "weapon_proficiencies"),
        ("tools", "tool_proficiencies"),
    ):
        state[stat] = deepcopy(character.equipment_proficiencies.get(category, []))
    for skill, proficiency in character.skill_proficiencies.items():
        state[f"{skill}_proficiency"] = proficiency
    for ability in ABILITY_IDS:
        state[f"{ability}_score"] = character.ability_score(ability)
    for level in range(1, 10):
        state[f"spell_slots_{level}"] = int(
            character.spell_slot_current.get(
                str(level),
                character.spell_slot_current.get(f"level-{level}", 0),
            )
        )
        adjustment = character.spell_slot_adjustments.get(
            str(level),
            character.spell_slot_adjustments.get(f"level-{level}", 0),
        )
        if isinstance(adjustment, int) and not isinstance(adjustment, bool):
            state[f"max_spell_slots_{level}_bonus"] = adjustment
    return state


def hydrated_native_state(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the current native definition and fully linked character state.

    This intentionally has no persistence side effects.  It is used for read
    projections which must be calculated by the same interpreter as a real
    character event.
    """
    source = character_native_source(character)
    definition = hoard_native_definition(source)
    state = (
        deepcopy(character.native_state)
        if character.native_state
        else initial_native_state(character, definition)
    )
    hydrate_linked_resources(character, state)

    return definition, state


def preview_character_event_state(
    character: Character,
    event_name: str,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate an event without modifying the character or recording history."""
    definition, state = hydrated_native_state(character)
    execution = NativeRuntime(definition, state).fire(event_name, payload)

    return definition, execution.state


def native_spell_slot_pools(character: Character) -> dict[str, dict[str, int]]:
    """Return slot values and long-rest maxima from the native system runtime."""
    definition, current_state = hydrated_native_state(character)
    maximum_state = NativeRuntime(definition, current_state).fire("long_rest").state
    current_evaluator = NativeEvaluator(definition, current_state)
    maximum_evaluator = NativeEvaluator(definition, maximum_state)
    current_scope = NativeScope(values=current_state, character=current_state)
    maximum_scope = NativeScope(values=maximum_state, character=maximum_state)
    levels = sorted(
        (
            identifier.removeprefix("spell_slots_")
            for identifier in current_evaluator.stat_definitions
            if identifier.startswith("spell_slots_")
            and identifier.removeprefix("spell_slots_").isdigit()
        ),
        key=int,
    )
    pools: dict[str, dict[str, int]] = {}

    for level in levels:
        current = current_evaluator.stat(f"spell_slots_{level}", current_scope)
        maximum = maximum_evaluator.stat(f"spell_slots_{level}", maximum_scope)
        adjustment = current_evaluator.stat(
            f"max_spell_slots_{level}_bonus", current_scope
        )
        current_value = current if isinstance(current, int) and not isinstance(current, bool) else 0
        maximum_value = maximum if isinstance(maximum, int) and not isinstance(maximum, bool) else 0
        adjustment_value = (
            adjustment
            if isinstance(adjustment, int) and not isinstance(adjustment, bool)
            else 0
        )
        pools[level] = {
            "calculated": max(0, maximum_value - adjustment_value),
            "adjustment": adjustment_value,
            "maximum": max(0, maximum_value),
            "current": min(max(0, current_value), max(0, maximum_value)),
        }

    return pools


def native_spellcasting_classes(character: Character) -> list[dict[str, object]]:
    """Resolve each spellcasting class through the native resource formulas."""
    definition, state = hydrated_native_state(character)
    class_details_definition = next(
        (
            resource
            for resource in definition.get("resources", [])
            if isinstance(resource, dict) and resource.get("id") == "class_details"
        ),
        None,
    )
    if class_details_definition is None:
        return []

    character_evaluator = NativeEvaluator(definition, state)
    classes: list[dict[str, object]] = []
    for detail in native_class_detail_values(state):
        stats = detail["stats"]
        evaluator = NativeEvaluator(
            class_details_definition,
            stats,
            character_evaluator=character_evaluator,
        )
        scope = NativeScope(values=stats, character=state, parent=state)
        is_spellcaster = evaluator.stat("show_spellcasting_details", scope)
        ability = evaluator.stat("class.actual_spellcasting_ability", scope)
        attack = evaluator.stat("spell_attack_bonus", scope)
        save_dc = evaluator.stat("spell_save_dc", scope)
        name = evaluator.stat("class.name", scope)

        if not is_spellcaster or not isinstance(ability, str) or not isinstance(name, str):
            continue
        if not isinstance(attack, int) or isinstance(attack, bool):
            continue
        if not isinstance(save_dc, int) or isinstance(save_dc, bool):
            continue
        classes.append(
            {
                "name": name,
                "ability": ability,
                "spell_attack": attack,
                "spell_save_dc": save_dc,
            }
        )

    return classes


def execute_character_event(
    character: Character,
    event_name: str,
    payload: dict[str, Any] | None = None,
    *,
    created_by: CampaignContext | None = None,
    effects: dict[str, Any] | list[Any] | None = None,
    resource_updates: dict[str, dict[str, Any]] | None = None,
    removed_resource_identifier: str = "",
    view_values: dict[str, Any] | None = None,
) -> NativeCommandResult:
    """Execute, persist, project, and audit one native character event."""
    with transaction.atomic():
        locked = (
            Character.objects.select_for_update()
            .select_related("campaign")
            .get(pk=character.pk)
        )
        source = character_native_source(locked)
        definition = hoard_native_definition(source)
        if effects is not None:
            mechanics = definition.setdefault("mechanics", [])
            mechanics.append(
                {
                    "id": f"hoard_adapter_{event_name}",
                    "event_names": event_name,
                    "effects": deepcopy(effects),
                }
            )
        state = (
            deepcopy(locked.native_state)
            if locked.native_state
            else initial_native_state(locked, definition)
        )
        hydrate_linked_resources(locked, state)
        apply_resource_updates(state, resource_updates or {})
        runtime = NativeRuntime(definition, state, view_values=view_values)
        execution = (
            runtime.remove_resource(removed_resource_identifier, event_name)
            if removed_resource_identifier
            else runtime.fire(event_name, payload)
        )
        if execution.delayed_effects:
            runtime_state = execution.state.setdefault("$hoard_runtime", {})
            delayed = runtime_state.setdefault("delayed", [])
            delayed.extend(deepcopy(execution.delayed_effects))

        locked.native_state = execution.state
        locked.native_system_source = source
        locked.native_system_id = source.identifier
        locked.native_system_version = source.version
        project_native_state(locked, definition)
        event = CharacterNativeEvent.objects.create(
            campaign=locked.campaign,
            character=locked,
            created_by=created_by,
            event_name=event_name,
            payload=payload or {},
            system_identifier=source.identifier,
            system_version=source.version,
            system_checksum=source.package_checksum,
            fired_events=execution.fired_events,
            changes=execution.changes,
            messages=execution.messages,
            interface_actions=execution.interface_actions,
            delayed_effects=execution.delayed_effects,
            unsupported=execution.unsupported,
        )
        for delayed_effect in execution.delayed_effects:
            transaction.on_commit(
                partial(
                    schedule_delayed_effect,
                    locked.pk,
                    deepcopy(delayed_effect),
                )
            )
    return NativeCommandResult(character=locked, execution=execution, event=event)


def schedule_delayed_effect(
    character_id: int,
    delayed_effect: dict[str, Any],
) -> None:
    """Queue authoritative delayed work after the originating transaction commits."""
    from ..tasks import run_native_delayed_effect

    countdown = max(0, int(delayed_effect.get("millis", 0))) / 1000
    run_native_delayed_effect.apply_async(
        args=(character_id, str(delayed_effect.get("id", ""))),
        countdown=countdown,
    )


def execute_due_delayed_effect(
    character_id: int,
    delayed_id: str,
) -> NativeCommandResult | None:
    """Consume and persist one queued delayed native effect exactly once."""
    with transaction.atomic():
        character = (
            Character.objects.select_for_update()
            .select_related("campaign")
            .get(pk=character_id)
        )
        runtime_state = character.native_state.get("$hoard_runtime", {})
        delayed_effects = runtime_state.get("delayed", [])
        delayed = next(
            (
                value
                for value in delayed_effects
                if isinstance(value, dict) and value.get("id") == delayed_id
            ),
            None,
        )
        if delayed is None:
            return None
        due_at = datetime.fromisoformat(str(delayed["due_at"]))
        now = datetime.now(due_at.tzinfo)
        if due_at > now:
            raise ValidationError("The delayed native effect is not due yet.")
        source = character_native_source(character)
        definition = hoard_native_definition(source)
        state = deepcopy(character.native_state)
        state["$hoard_runtime"]["delayed"] = [
            value
            for value in delayed_effects
            if not (isinstance(value, dict) and value.get("id") == delayed_id)
        ]
        runtime = NativeRuntime(definition, state)
        execution = runtime.execute_delayed(delayed)
        if execution.delayed_effects:
            execution.state["$hoard_runtime"]["delayed"].extend(
                deepcopy(execution.delayed_effects)
            )
        character.native_state = execution.state
        project_native_state(character, definition)
        event = CharacterNativeEvent.objects.create(
            campaign=character.campaign,
            character=character,
            event_name=f"rpg_delayed:{delayed_id}",
            payload={},
            system_identifier=source.identifier,
            system_version=source.version,
            system_checksum=source.package_checksum,
            fired_events=execution.fired_events,
            changes=execution.changes,
            messages=execution.messages,
            interface_actions=execution.interface_actions,
            delayed_effects=execution.delayed_effects,
            unsupported=execution.unsupported,
        )
        for child in execution.delayed_effects:
            transaction.on_commit(
                partial(schedule_delayed_effect, character.pk, deepcopy(child))
            )
    return NativeCommandResult(character=character, execution=execution, event=event)


def hydrate_linked_resources(character: Character, state: dict[str, Any]) -> None:
    """Expose direct compendium relationships through native character stats."""
    relationships = [
        *character.native_resources.all(),
        *character.spells.all(),
        *character.inventory.keys(),
    ]
    if character.race_entry_id:
        relationships.append(character.race_entry)
    if character.background_entry_id:
        relationships.append(character.background_entry)
    by_stat: dict[str, list[dict[str, Any]]] = {}
    saved_resource_state = state.get("$hoard_resource_state", {})
    for entry in relationships:
        if entry.kind == CompendiumEntry.Kind.CLASS:
            continue
        resource = deepcopy(entry.data)
        if not isinstance(resource, dict) or resource.get("resource_id") != entry.kind:
            continue
        resource["$hoard_entry_id"] = entry.pk
        saved_values = (
            saved_resource_state.get(str(entry.pk), {})
            if isinstance(saved_resource_state, dict)
            else {}
        )
        stats = resource.get("stats")
        if isinstance(stats, dict) and isinstance(saved_values, dict):
            for stat, value in saved_values.items():
                assign_native_value(stats, stat, value)
        stat = character_resource_stat(entry.kind)
        by_stat.setdefault(stat, []).append(resource)
    for stat, resources in by_stat.items():
        state[stat] = resources
    hydrate_native_classes(character, state)


def native_sheet_view(
    character: Character,
    excluded_section_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Resolve native sheet views for Hoard's generic, styled renderer."""
    try:
        source = character_native_source(character)
    except ValidationError as error:
        return {
            "available": False,
            "system_id": character.native_system_id,
            "version": character.native_system_version,
            "sections": [],
            "diagnostics": [str(error)],
        }
    source_sections = source.system_definition.get("character_sheet_sections", [])
    visible_sections = [
        section
        for section in source_sections
        if isinstance(section, dict)
        and section.get("id") not in excluded_section_ids
    ]
    if not visible_sections:
        return {
            "available": True,
            "system_id": source.identifier,
            "version": source.version,
            "sections": [],
            "diagnostics": [],
        }

    definition = hoard_native_definition(source)
    state = (
        deepcopy(character.native_state)
        if character.native_state
        else initial_native_state(character, definition)
    )
    hydrate_linked_resources(character, state)
    evaluator = NativeEvaluator(definition, state)
    scope = NativeScope(values=state, character=state)
    diagnostics: list[str] = []

    def resolve(value: Any) -> Any:
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return value
        node_type = value.get("type")
        formula_handler = (
            getattr(evaluator, f"evaluate_{node_type}", None)
            if isinstance(node_type, str)
            and not (
                node_type in SUPPORTED_NATIVE_VIEW_TYPES
                and isinstance(value.get("id"), str)
            )
            else None
        )
        if formula_handler is not None:
            try:
                return {
                    "value": evaluator.evaluate(value, scope),
                    "formula": deepcopy(value),
                }
            except (NativeRuntimeError, TypeError, ValueError, ZeroDivisionError) as error:
                diagnostics.append(str(error))
                return {"value": None, "formula": deepcopy(value), "error": str(error)}
        rendered = {key: resolve(item) for key, item in value.items()}
        stat = value.get("stat")
        if isinstance(stat, str):
            rendered["current_value"] = evaluator.stat(stat, scope)
        resource_stat = value.get("resource_stat")
        if isinstance(resource_stat, str):
            rendered["current_resources"] = deepcopy(state.get(resource_stat, []))
        if node_type == "select":
            enumeration = evaluator.enumerated_types.get(
                str(value.get("enumerated_type", "")), {}
            )
            options = enumeration.get(
                "types", enumeration.get("options", enumeration.get("values", []))
            )
            if isinstance(options, list):
                rendered["resolved_options"] = deepcopy(options)
        if node_type in {"button", "menuButton", "popUpButton", "ticker"}:
            rendered["system_behaviour"] = {
                "event": resolve(value.get("event") or value.get("on_click_event")),
                "control": value.get("id"),
            }
        return rendered

    sections = [
        {
            "id": section.get("id", "section"),
            "view": resolve(section.get("view", {})),
        }
        for section in visible_sections
        if isinstance(section, dict)
    ]
    return {
        "available": True,
        "system_id": source.identifier,
        "version": source.version,
        "sections": sections,
        "diagnostics": list(dict.fromkeys(diagnostics)),
    }


def native_class_details(
    entry: CompendiumEntry,
    *,
    class_level: int,
    archetype_id: str = "",
    selected_feature_ids: list[str] | None = None,
    last_selection_level: int = 0,
) -> dict[str, Any]:
    """Build the upstream ``class_details`` state for one selected class.

    RPG Companion represents a multiclass character as one class-details
    resource per class.  Its level, archetype and selected feature IDs belong
    to that resource, rather than to a separate row for each character level.
    """
    if entry.kind != CompendiumEntry.Kind.CLASS:
        raise ValidationError("A class-details resource requires a class entry.")
    if class_level < 1:
        raise ValidationError("A class level must be at least one.")

    class_resource = deepcopy(entry.data)
    resource_id = class_resource.get("resource_id")
    if resource_id != CompendiumEntry.Kind.CLASS:
        raise ValidationError("The selected Compendium entry is not a native class.")
    class_resource["$hoard_entry_id"] = entry.pk
    identifier = native_resource_identifier(class_resource) or entry.source_identifier

    return {
        "resource_id": "class_details",
        "stats": {
            "id": {"value": f"class-details:{identifier}"},
            "class": {"value": class_resource},
            "archetype_id": {"value": archetype_id or None},
            "class_level": {"value": class_level},
            "selected_selectable_feature_ids": {
                "value": list(selected_feature_ids or [])
            },
            "last_selection_level": {"value": last_selection_level},
        },
    }


def native_class_detail_values(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return well-formed class-details resources held in native state."""
    resources = state.get("classes")
    if not isinstance(resources, list):
        return []
    return [
        resource
        for resource in resources
        if isinstance(resource, dict)
        and resource.get("resource_id") == "class_details"
        and isinstance(resource.get("stats"), dict)
    ]


def native_class_level(state: dict[str, Any]) -> int:
    """Return total character level from upstream class-details resources."""
    total = 0
    for detail in native_class_detail_values(state):
        value = detail["stats"].get("class_level")
        level = value.get("value") if isinstance(value, dict) else None
        if isinstance(level, int) and not isinstance(level, bool):
            total += max(0, level)
    return total


def native_class_summary(state: dict[str, Any]) -> str:
    """Format the native class-details state for Hoard's compact projection."""
    labels: list[str] = []
    for detail in native_class_detail_values(state):
        class_value = detail["stats"].get("class")
        resource = class_value.get("value") if isinstance(class_value, dict) else None
        stats = resource.get("stats") if isinstance(resource, dict) else None
        name_value = stats.get("name") if isinstance(stats, dict) else None
        name = name_value.get("value") if isinstance(name_value, dict) else ""
        level_value = detail["stats"].get("class_level")
        level = level_value.get("value") if isinstance(level_value, dict) else None
        if isinstance(name, str) and name and isinstance(level, int):
            labels.append(f"{name} {level}")
    return " / ".join(labels)


def hydrate_native_classes(character: Character, state: dict[str, Any]) -> None:
    """Refresh class content from linked Compendium entries without replacing state.

    Only the immutable class definition comes from the Compendium.  The
    class-details wrapper is the character's authoritative RPG Companion
    state, so its level, archetype and feature selections survive every event.
    """
    entries = {
        entry.pk: entry
        for entry in character.native_resources.filter(
            kind=CompendiumEntry.Kind.CLASS
        )
    }
    if not entries:
        return

    for detail in native_class_detail_values(state):
        class_value = detail["stats"].get("class")
        class_resource = (
            class_value.get("value") if isinstance(class_value, dict) else None
        )
        entry_id = (
            class_resource.get("$hoard_entry_id")
            if isinstance(class_resource, dict)
            else None
        )
        entry = entries.get(entry_id) if isinstance(entry_id, int) else None
        if entry is None:
            continue
        refreshed = deepcopy(entry.data)
        refreshed["$hoard_entry_id"] = entry.pk
        detail["stats"]["class"] = {"value": refreshed}


def apply_resource_updates(
    state: dict[str, Any], updates: dict[str, dict[str, Any]]
) -> None:
    """Apply event-local values to one linked native resource instance."""
    if not updates:
        return
    saved_resource_state = state.setdefault("$hoard_resource_state", {})
    for resource, parent in native_resources(state):
        identifier = native_resource_identifier(resource)
        values = updates.get(identifier)
        stats = resource.get("stats")
        if values is None or not isinstance(stats, dict):
            continue
        for stat, value in values.items():
            assign_native_value(stats, stat, value)
            entry_id = resource.get("$hoard_entry_id")
            if isinstance(entry_id, int) and isinstance(saved_resource_state, dict):
                saved_resource_state.setdefault(str(entry_id), {})[stat] = deepcopy(
                    value
                )


def execute_projection_update(
    character: Character,
    fields: dict[str, Any],
    *,
    created_by: CampaignContext | None = None,
    event_name: str = "hoard.character.update",
) -> NativeCommandResult:
    """Translate editable Hoard fields into one authoritative native event."""
    effects = []
    for field, value in fields.items():
        targets = projection_update_targets(field, value)
        for stat, native_value in targets.items():
            effects.append(
                {
                    "type": "setStat",
                    "stat": stat,
                    "new_value": {"type": "constant", "value": native_value},
                    "aggregation_type": "set",
                }
            )
    return execute_character_event(
        character,
        event_name,
        {"fields": deepcopy(fields)},
        created_by=created_by,
        effects={"type": "sequence", "effects": effects},
    )


def projection_update_targets(field: str, value: Any) -> dict[str, Any]:
    """Map one Hoard projection field to its native source stat or stats."""
    if field in NATIVE_TEXT_FIELDS or field == "base_hp":
        return {field: value}
    if field in ABILITY_IDS:
        return {f"{field}_score": value}
    if field == "languages":
        return {"language_proficiencies": value}
    if field == "equipment_proficiencies" and isinstance(value, dict):
        return {
            "armor_proficiencies": value.get("armor", []),
            "weapon_proficiencies": value.get("weapons", []),
            "tool_proficiencies": value.get("tools", []),
        }
    if field == "skill_proficiencies" and isinstance(value, dict):
        return {
            f"{skill}_proficiency": proficiency
            for skill, proficiency in value.items()
        }
    if field == "spell_slot_current" and isinstance(value, dict):
        return {
            f"spell_slots_{level}": amount
            for raw_level, amount in value.items()
            if (level := str(raw_level).removeprefix("level-")) in set("123456789")
        }
    if field == "spell_slot_adjustments" and isinstance(value, dict):
        targets = {"hoard_spell_slot_adjustments": value}
        for raw_level, amount in value.items():
            level = str(raw_level).removeprefix("level-")
            if level in set("123456789"):
                targets[f"max_spell_slots_{level}_bonus"] = amount
        return targets
    if field in HOARD_PROJECTED_FIELDS:
        return {f"hoard_{field}": value}
    raise ValidationError(f"{field} does not have a native projection mapping.")


def character_resource_stat(resource_id: str) -> str:
    """Map native resource IDs to the conventional character collection stat."""
    irregular = {
        "armor": "armors",
        "class_details": "classes",
        "race": "race",
        "background": "background",
    }
    return irregular.get(resource_id, f"{resource_id}s")


def project_native_state(character: Character, definition: dict[str, Any]) -> None:
    """Update non-authoritative Hoard columns from effective native values."""
    evaluator = NativeEvaluator(definition, character.native_state)
    scope = evaluator.default_state()
    evaluator = NativeEvaluator(definition, scope)
    native_scope = evaluator_scope(scope)
    update_fields = [
        "native_state",
        "native_system_source",
        "native_system_id",
        "native_system_version",
    ]

    scalar_fields = {
        "name": "name",
        "base_hp": "base_hp",
        "current_hp": "current_hp",
        "hoard_temporary_hp": "temporary_hp",
    }
    for native_id, field_name in scalar_fields.items():
        value = evaluator.stat(native_id, native_scope)
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            setattr(character, field_name, value)
            update_fields.append(field_name)

    for field in NATIVE_TEXT_FIELDS:
        value = evaluator.stat(field, native_scope)
        if isinstance(value, str):
            setattr(character, field, value)
            update_fields.append(field)
    for field in HOARD_PROJECTED_FIELDS:
        value = evaluator.stat(f"hoard_{field}", native_scope)
        setattr(character, field, deepcopy(value))
        update_fields.append(field)
    character.character_class = native_class_summary(character.native_state)
    update_fields.append("character_class")
    languages = evaluator.stat("language_proficiencies", native_scope)
    if isinstance(languages, list):
        character.languages = languages
        update_fields.append("languages")
    equipment = {}
    for category, stat in (
        ("armor", "armor_proficiencies"),
        ("weapons", "weapon_proficiencies"),
        ("tools", "tool_proficiencies"),
    ):
        value = evaluator.stat(stat, native_scope)
        equipment[category] = value if isinstance(value, list) else []
    character.equipment_proficiencies = equipment
    update_fields.append("equipment_proficiencies")
    skills = {}
    for stat_id in evaluator.stat_definitions:
        if not stat_id.endswith("_proficiency"):
            continue
        skill = stat_id.removesuffix("_proficiency")
        if skill in {"armor", "weapon", "tool"}:
            continue
        value = evaluator.stat(stat_id, native_scope)
        if isinstance(value, str):
            skills[skill] = value
    if skills:
        character.skill_proficiencies = skills
        update_fields.append("skill_proficiencies")

    for ability in ABILITY_IDS:
        value = evaluator.stat(f"{ability}_score", native_scope)
        if isinstance(value, int) and not isinstance(value, bool):
            bonuses = int(character.ability_bonuses.get(ability, 0))
            adjustments = int(character.ability_score_adjustments.get(ability, 0))
            setattr(character, ability, max(1, value - bonuses - adjustments))
            update_fields.append(ability)
    slots = deepcopy(character.spell_slot_current)
    for level in range(1, 10):
        value = evaluator.stat(f"spell_slots_{level}", native_scope)
        if isinstance(value, int) and not isinstance(value, bool):
            slots[str(level)] = max(0, value)
    character.spell_slot_current = slots
    update_fields.append("spell_slot_current")
    inspiration = evaluator.stat("hoard_inspiration", native_scope)
    if isinstance(inspiration, bool):
        character.has_inspiration = inspiration
        update_fields.append("has_inspiration")
    expiry = evaluator.stat("hoard_inspiration_expires_at", native_scope)
    if isinstance(expiry, str):
        try:
            character.inspiration_expires_at = datetime.fromisoformat(expiry)
        except ValueError:
            character.inspiration_expires_at = None
        update_fields.append("inspiration_expires_at")
    character.save(update_fields=tuple(dict.fromkeys(update_fields)))


def evaluator_scope(state: dict[str, Any]):
    """Construct the ordinary character scope without exposing runtime internals."""
    from hoard.compendium.native.runtime import NativeScope

    return NativeScope(values=state, character=state)
