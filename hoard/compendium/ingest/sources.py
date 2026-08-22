"""Translate RPG Companion resource files into Compendium entries."""

from __future__ import annotations

import json
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from hoard.compendium.models import CompendiumEntry, CompendiumSource

ENTRY_KINDS = frozenset(CompendiumEntry.Kind.values)
CURRENCIES = {
    "copper": "cp",
    "silver": "sp",
    "electrum": "ep",
    "gold": "gp",
    "platinum": "pp",
    "cp": "cp",
    "sp": "sp",
    "ep": "ep",
    "gp": "gp",
    "pp": "pp",
}


def import_source_directory(
    directory: Path, source: CompendiumSource
) -> tuple[int, int, int]:
    """Upsert one source's supported resource files and retain encounter templates."""
    resources: list[tuple[dict[str, Any], str]] = []
    for path in directory.rglob("*.rpg.json"):
        resource = _read_resource(path)
        if resource is not None:
            resources.append((resource, path.stem))
    return import_resources(resources, source)


def import_resources(
    resources: Iterable[tuple[dict[str, Any], str]], source: CompendiumSource
) -> tuple[int, int, int]:
    """Upsert supported RPG Companion resources from any package representation."""
    created = updated = skipped = 0
    encounters: list[dict[str, object]] = []
    for resource, fallback_identifier in resources:
        if resource.get("resource_id") == "encounter_template":
            encounters.append(resource)
            continue
        result = _import_entry(resource, fallback_identifier, source)
        created += result == "created"
        updated += result == "updated"
        skipped += result == "skipped"
    source.data = {**source.data, "encounter_templates": encounters}
    source.save(update_fields=("data",))
    return created, updated, skipped


def _read_resource(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _import_entry(
    resource: dict[str, Any], fallback_identifier: str, source: CompendiumSource
) -> str:
    kind = resource.get("resource_id")
    stats = resource.get("stats")
    if kind not in ENTRY_KINDS or not isinstance(stats, dict):
        return "skipped"
    name = _value(stats, "name")
    if not isinstance(name, str) or not name.strip():
        return "skipped"
    identifier = _value(stats, "id")
    source_book = _value(stats, "source")
    description = _value(stats, "description")
    _, created = CompendiumEntry.objects.update_or_create(
        source=source,
        kind=kind,
        source_identifier=identifier
        if isinstance(identifier, str)
        else fallback_identifier,
        defaults={
            "name": name.strip(),
            "source_book": source_book if isinstance(source_book, str) else "",
            "description": description if isinstance(description, str) else "",
            "data": resource,
            **_equipment_fields(stats),
        },
    )
    return "created" if created else "updated"


def _value(values: dict[str, Any], name: str) -> object | None:
    value = values.get(name)
    return value.get("value") if isinstance(value, dict) else value


def _equipment_fields(stats: dict[str, Any]) -> dict[str, object]:
    cost = _nested_stat(_value(stats, "cost"))
    weight = _nested_stat(_value(stats, "weight"))
    return {
        "cost_amount": _decimal(cost.get("value", stats.get("cost"))),
        "cost_currency": _currency(cost.get("unit")),
        "weight_amount": _decimal(weight.get("value", stats.get("weight"))),
        "weight_unit": weight.get("unit")
        if isinstance(weight.get("unit"), str)
        else "",
        "rarity": _string(stats, "rarity"),
        "is_magic": _boolean(stats, "is_magic", "isMagical"),
        "requires_attunement": _boolean(
            stats, "requires_attunement", "requiresAttunement"
        ),
    }


def _nested_stat(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not isinstance(value.get("stats"), dict):
        return {}
    return {name: _value(value["stats"], name) for name in ("value", "unit")}


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation, ValueError:
        return None


def _currency(value: object) -> str:
    return CURRENCIES.get(value.lower(), "") if isinstance(value, str) else ""


def _string(values: dict[str, Any], name: str) -> str:
    value = _value(values, name)
    return value if isinstance(value, str) else ""


def _boolean(values: dict[str, Any], *names: str) -> bool | None:
    for name in names:
        value = _value(values, name)
        if isinstance(value, bool):
            return value
    return None
