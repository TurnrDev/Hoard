from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from hoard.campaigns.models import Campaign
from hoard.compendium.ingest.registry import sync_registry
from hoard.compendium.ingest.repository import import_directory, import_repository
from hoard.compendium.models import CompendiumRepository

BUNDLED_DEFAULT = Path(__file__).resolve().parents[2] / "systems" / "default"
COMPILED_DEFAULT = Path(__file__).resolve().parents[2] / "systems" / "compiled"


class Command(BaseCommand):
    help = "Synchronize the community registry and import its default repository."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--source", type=Path, help="Local checkout for default.")
        parser.add_argument("--ref", default="", help="Optional GitHub branch or tag.")
        parser.add_argument(
            "--remote",
            action="store_true",
            help="Import the registry's remote default instead of Hoard's bundled fork.",
        )
        parser.add_argument(
            "--no-registry",
            action="store_true",
            help="Do not contact the community registry.",
        )
        parser.add_argument(
            "--if-missing",
            action="store_true",
            help="Skip import when complete default 5e definitions already exist.",
        )

    def handle(self, *args: object, **options: object) -> None:
        default = CompendiumRepository.objects.filter(identifier="default").first()
        if options["if_missing"] and default is not None:
            installed = set(
                default.sources.exclude(system_definition={}).values_list(
                    "identifier", flat=True
                )
            )
            if {"5e", "5e2024"}.issubset(installed):
                enable_default_systems(default)
                self.stdout.write("Default native systems are already installed.")
                return
        if not options["no_registry"]:
            try:
                default = sync_registry().get("default", default)
            except ValidationError as error:
                if options["remote"] or default is None:
                    raise CommandError(error.messages[0]) from error
                self.stderr.write(
                    self.style.WARNING(
                        "Could not refresh the community registry; using bundled default."
                    )
                )
        if default is None:
            default = CompendiumRepository.objects.create(
                identifier="default",
                name="RPG Companion default (Hoard fork)",
                description="Bundled Hoard fork of the RPG Companion open systems.",
                github_repository="blastervla/rpg-companion-app-systems",
            )

        checkout = options["source"]
        try:
            if checkout:
                if not checkout.is_dir():
                    raise CommandError(f"Source directory does not exist: {checkout}")
                counts = import_directory(checkout, default, {"5e", "5e2024"})
            elif options["remote"]:
                counts = import_repository(
                    default,
                    ref=str(options["ref"]),
                    source_identifiers={"5e", "5e2024"},
                )
            else:
                bundled = (
                    COMPILED_DEFAULT
                    if os.environ.get("HOARD_USE_COMPILED_SYSTEMS", "").lower()
                    in {"1", "true", "yes", "on"}
                    and (COMPILED_DEFAULT / "systems.rpg").is_file()
                    else BUNDLED_DEFAULT
                )
                counts = import_directory(
                    bundled,
                    default,
                    {"5e", "5e2024"},
                )
        except ValidationError as error:
            raise CommandError(error.messages[0]) from error

        enable_default_systems(default)
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated repositories; {counts[0]} entries created, "
                f"{counts[1]} updated, {counts[2]} skipped."
            )
        )


def enable_default_systems(repository: CompendiumRepository) -> None:
    """Give campaigns an initial baseline without overriding an explicit choice."""
    sources = {
        source.identifier: source
        for source in repository.sources.filter(identifier__in=("5e", "5e2024"))
        if source.system_definition
    }
    if not sources:
        return

    for campaign in Campaign.objects.filter(native_system_source__isnull=True):
        source = sources.get(campaign.native_system_id) or sources.get("5e")
        if source is None:
            continue
        campaign.native_system_source = source
        campaign.native_system_id = source.identifier
        campaign.save(update_fields=("native_system_source", "native_system_id"))
        campaign.compendium_sources.add(*sources.values())
