from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from hoard.compendium.ingest.registry import sync_registry
from hoard.compendium.ingest.repository import import_directory, import_repository


class Command(BaseCommand):
    help = "Synchronize the community registry and import its default repository."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--source", type=Path, help="Local checkout for default.")
        parser.add_argument("--ref", default="", help="Optional GitHub branch or tag.")

    def handle(self, *args: object, **options: object) -> None:
        try:
            default = sync_registry().get("default")
        except ValidationError as error:
            raise CommandError(error.messages[0]) from error
        if default is None:
            raise CommandError("The community registry has no default repository.")

        checkout = options["source"]
        try:
            if checkout:
                if not checkout.is_dir():
                    raise CommandError(f"Source directory does not exist: {checkout}")
                counts = import_directory(checkout, default, {"5e", "5e2024"})
            else:
                counts = import_repository(
                    default,
                    ref=str(options["ref"]),
                    source_identifiers={"5e", "5e2024"},
                )
        except ValidationError as error:
            raise CommandError(error.messages[0]) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated repositories; {counts[0]} entries created, "
                f"{counts[1]} updated, {counts[2]} skipped."
            )
        )
