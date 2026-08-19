from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hoard.campaigns.models import InventoryItem

SOURCE_REPOSITORY = "https://github.com/blastervla/rpg-companion-app-systems"
SYSTEMS = ("5e", "5e2024")
EQUIPMENT_RESOURCE_IDS = ("item", "weapon", "armor")
CURRENCY_UNITS = {
    "copper": "cp",
    "silver": "sp",
    "electrum": "ep",
    "gold": "gp",
    "platinum": "pp",
}


def _stat_value(stats: dict[str, Any], name: str) -> object | None:
    value = stats.get(name)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _nested_stat_value(value: object, name: str) -> object | None:
    if not isinstance(value, dict):
        return None
    stats = value.get("stats")
    return _stat_value(stats, name) if isinstance(stats, dict) else None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation, ValueError:
        return None


def _equipment_defaults(
    resource: dict[str, Any], resource_id: str, stats: dict[str, Any]
) -> dict[str, object]:
    cost = _stat_value(stats, "cost")
    weight = _stat_value(stats, "weight")
    raw_cost_currency = _nested_stat_value(cost, "unit")
    raw_weight_unit = _nested_stat_value(weight, "unit")
    cost_currency = (
        CURRENCY_UNITS.get(raw_cost_currency)
        if isinstance(raw_cost_currency, str)
        else None
    )
    return {
        "campaign": None,
        "created_by": None,
        "name": _stat_value(stats, "name"),
        "description": _stat_value(stats, "description")
        if isinstance(_stat_value(stats, "description"), str)
        else "",
        "source_book": _stat_value(stats, "source")
        if isinstance(_stat_value(stats, "source"), str)
        else "",
        "equipment_category": resource_id,
        "item_type": _stat_value(stats, "type")
        if isinstance(_stat_value(stats, "type"), str)
        else "",
        "cost_amount": _decimal(_nested_stat_value(cost, "value"))
        if cost_currency
        else None,
        "cost_currency": cost_currency or "",
        "weight_amount": _decimal(_nested_stat_value(weight, "value")),
        "weight_unit": raw_weight_unit if isinstance(raw_weight_unit, str) else "",
        "rarity": _stat_value(stats, "rarity")
        if isinstance(_stat_value(stats, "rarity"), str)
        else "",
        "is_magic": _stat_value(stats, "is_magic")
        if isinstance(_stat_value(stats, "is_magic"), bool)
        else None,
        "requires_attunement": _stat_value(stats, "requires_attunement")
        if isinstance(_stat_value(stats, "requires_attunement"), bool)
        else None,
        "source_data": resource,
    }


def _upsert_equipment(
    *, system: str, resource_id: str, identifier: str, defaults: dict[str, object]
) -> tuple[InventoryItem, bool]:
    """Upsert equipment and upgrade records made by the pre-category importer.

    Earlier versions imported only generic items and left their category blank.
    Updating those records in place preserves any immutable ledger entries that
    refer to them. An unreferenced duplicate from an earlier rich import is
    discarded before the legacy record is upgraded.
    """
    lookup = {
        "source_repository": SOURCE_REPOSITORY,
        "source_system": system,
        "equipment_category": resource_id,
        "source_identifier": identifier,
    }
    if resource_id == "item":
        legacy = InventoryItem.objects.filter(
            source_repository=SOURCE_REPOSITORY,
            source_system=system,
            source_identifier=identifier,
            equipment_category="",
        ).first()
        if legacy is not None:
            current = InventoryItem.objects.filter(**lookup).first()
            if current is None or not current.entries.exists():
                if current is not None:
                    current.delete()
                for field, value in defaults.items():
                    setattr(legacy, field, value)
                legacy.save()
                return legacy, False
    return InventoryItem.objects.update_or_create(**lookup, defaults=defaults)


class Command(BaseCommand):
    help = "Import global 5e and 5e2024 item resources from rpg-companion-app-systems."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--source",
            type=Path,
            default=settings.BASE_DIR / "vendor" / "rpg-companion-app-systems",
            help="Path to the checked-out rpg-companion-app-systems repository.",
        )

    def handle(self, *args: object, **options: object) -> None:
        source = Path(options["source"])
        if not source.is_dir():
            raise CommandError(f"Item source directory does not exist: {source}")
        created = 0
        updated = 0
        skipped = 0
        for system in SYSTEMS:
            resource_directory = source / "systems" / system / "resource_instances"
            if not resource_directory.is_dir():
                raise CommandError(
                    f"Missing resource directory for {system}: {resource_directory}"
                )
            for path in resource_directory.glob("*.rpg.json"):
                try:
                    resource = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as error:
                    raise CommandError(f"Invalid JSON in {path}: {error}") from error
                resource_id = resource.get("resource_id")
                if resource_id not in EQUIPMENT_RESOURCE_IDS:
                    continue
                stats = resource.get("stats")
                identifier = (
                    _stat_value(stats, "id") if isinstance(stats, dict) else None
                )
                name = _stat_value(stats, "name") if isinstance(stats, dict) else None
                if (
                    not isinstance(identifier, str)
                    or not isinstance(name, str)
                    or not name
                ):
                    skipped += 1
                    continue
                item, was_created = _upsert_equipment(
                    system=system,
                    resource_id=resource_id,
                    identifier=identifier,
                    defaults=_equipment_defaults(resource, resource_id, stats),
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported items: {created} created, {updated} updated, {skipped} skipped."
            )
        )
