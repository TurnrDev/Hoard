"""Compose RPG Companion development and published system definitions."""

from __future__ import annotations

import gzip
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError

COLLECTION_DIRECTORIES = {
    "character_creation_flow": "character_creation_flow",
    "character_sheet_sections": "character_sheet_sections",
    "enumerated_types": "enumerated_types",
    "mechanics": "mechanics",
}
IDENTIFIED_COLLECTIONS = frozenset({"resources", "stats"})


def merge_native_values(base: Any, overlay: Any, key: str = "") -> Any:
    """Apply RPG Companion's recursive composition rules without losing order."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = deepcopy(base)
        for child_key, value in overlay.items():
            if child_key in merged:
                merged[child_key] = merge_native_values(
                    merged[child_key], value, child_key
                )
            else:
                merged[child_key] = deepcopy(value)
        return merged

    if isinstance(base, list) and isinstance(overlay, list):
        if key in IDENTIFIED_COLLECTIONS:
            return merge_identified_values(base, overlay)
        return [*deepcopy(base), *deepcopy(overlay)]

    return deepcopy(overlay)


def merge_identified_values(base: list[Any], overlay: list[Any]) -> list[Any]:
    """Merge objects with matching IDs in place and append new IDs in order."""
    result = deepcopy(base)
    positions = {
        value["id"]: index
        for index, value in enumerate(result)
        if isinstance(value, dict) and isinstance(value.get("id"), str)
    }
    for value in overlay:
        identifier = value.get("id") if isinstance(value, dict) else None
        if isinstance(identifier, str) and identifier in positions:
            index = positions[identifier]
            result[index] = merge_native_values(result[index], value)
            continue
        if isinstance(identifier, str):
            positions[identifier] = len(result)
        result.append(deepcopy(value))
    return result


def compose_development_system(directory: Path) -> dict[str, Any]:
    """Compose a development-layout system's JSON definitions.

    RPGScript files require the upstream compiler. A repository may include its
    compiled ``system.rpg`` beside the development sources; Hoard prefers that
    artifact and otherwise composes all JSON-form definitions losslessly.
    """
    published = directory / "system.rpg"
    if published.is_file():
        return read_published_system(published)

    system_directory = directory / "system"
    main = read_json_object(system_directory / "system.rpg.json")
    definition = deepcopy(main)

    character_stats = system_directory / "character_stats.rpg.json"
    if character_stats.is_file():
        definition["character_stats"] = read_json_value(character_stats)

    for field, relative_directory in COLLECTION_DIRECTORIES.items():
        values = compose_ordered_collection(system_directory / relative_directory)
        if values:
            existing = definition.get(field, [])
            definition[field] = merge_native_values(existing, values, field)

    resources = compose_resource_definitions(system_directory / "resources")
    if resources:
        definition["resources"] = merge_native_values(
            definition.get("resources", []), resources, "resources"
        )

    definition["hoard_composition"] = {
        "layout": "development",
        "rpgscript_compiled": not any(system_directory.rglob("*.rpgs")),
    }
    return definition


def compose_ordered_collection(directory: Path) -> list[Any]:
    """Compose lexically ordered JSON collection fragments in one directory."""
    if not directory.is_dir():
        return []
    result: list[Any] = []
    index = directory / "index.rpg.json"
    if index.is_file():
        result = collection_values(read_json_value(index))
    for path in sorted(directory.glob("*.rpg.json")):
        if path == index:
            continue
        result = merge_native_values(result, collection_values(read_json_value(path)))
    return result


def compose_resource_definitions(directory: Path) -> list[dict[str, Any]]:
    """Compose each split resource definition in lexical resource-ID order."""
    if not directory.is_dir():
        return []
    resources: list[dict[str, Any]] = []
    for resource_directory in sorted(path for path in directory.iterdir() if path.is_dir()):
        index = resource_directory / "index.rpg.json"
        if not index.is_file():
            continue
        resource = read_json_object(index)
        for field, filename in (
            ("stats", "stats.rpg.json"),
            ("display_view", "display_view.rpg.json"),
            ("edit_view", "edit_view.rpg.json"),
            ("list_view", "list_view.rpg.json"),
            ("search_item_view", "search_item_view.rpg.json"),
        ):
            path = resource_directory / filename
            if path.is_file():
                resource = merge_native_values(resource, {field: read_json_value(path)})
        mechanics = compose_ordered_collection(resource_directory / "mechanics")
        if mechanics:
            resource = merge_native_values(resource, {"mechanics": mechanics})
        resources.append(resource)
    return resources


def read_published_system(path: Path) -> dict[str, Any]:
    """Read a gzip-compressed published RPG Companion system definition."""
    try:
        payload = gzip.decompress(path.read_bytes())
        value = json.loads(payload)
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError("RPG Companion system definition is invalid.") from error
    if not isinstance(value, dict):
        raise ValidationError("RPG Companion system definition must be an object.")
    return value


def definition_checksum(definition: dict[str, Any]) -> str:
    """Return a stable digest for a composed native definition."""
    encoded = json.dumps(
        definition, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    """Read one JSON object with a source-oriented validation error."""
    value = read_json_value(path)
    if not isinstance(value, dict):
        raise ValidationError(f"{path.name} must contain a JSON object.")
    return value


def read_json_value(path: Path) -> Any:
    """Read one JSON value from a development package."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"Could not read {path.name}.") from error


def collection_values(value: Any) -> list[Any]:
    """Normalise collection indexes represented as a list or keyed object."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in (
            "items",
            "mechanics",
            "enumerated_types",
            "character_creation_flow",
            "character_sheet_sections",
        ):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
        return [value]
    return []
