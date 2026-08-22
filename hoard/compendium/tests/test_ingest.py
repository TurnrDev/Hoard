from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
from tarfile import TarInfo
from tarfile import open as open_tarfile
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, TestCase

from hoard.compendium.ingest.repository import (
    SUPPORTED_SOURCE_IDENTIFIERS,
    _read_published_resources,
    _read_rpg_json,
    _supported_source_identifiers,
)
from hoard.compendium.ingest.sources import import_source_directory as import_rpg
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)


class PublishedPackageTests(SimpleTestCase):
    def test_only_5e_sources_are_supported(self):
        self.assertEqual(SUPPORTED_SOURCE_IDENTIFIERS, {"5e", "5e2024"})
        self.assertEqual(_supported_source_identifiers({"5e", "pf2e"}), {"5e"})
        self.assertEqual(_supported_source_identifiers({"pf2e"}), set())

    def test_reads_rpg_companion_published_package(self):
        resource = {
            "resource_id": "background",
            "stats": {"id": {"value": "obojima-background"}},
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "systems.rpg").write_bytes(
                gzip.compress(json.dumps({"systems": [{"id": "5e"}]}).encode())
            )
            bundle = io.BytesIO()
            with open_tarfile(fileobj=bundle, mode="w") as archive:
                encoded_resource = gzip.compress(json.dumps(resource).encode())
                member = TarInfo("background/obojima-background.rpg")
                member.size = len(encoded_resource)
                archive.addfile(member, io.BytesIO(encoded_resource))
            (root / "resources.rpg.gzip").write_bytes(gzip.compress(bundle.getvalue()))

            self.assertEqual(
                _read_rpg_json(root / "systems.rpg"), {"systems": [{"id": "5e"}]}
            )
            self.assertEqual(
                _read_published_resources(root / "resources.rpg.gzip"),
                [(resource, "obojima-background")],
            )


class CompendiumIngestTests(TestCase):
    def _write_rpg_resource(
        self, root: Path, system: str, kind: str, identifier: str, name: str
    ) -> dict[str, object]:
        payload = {
            "resource_id": kind,
            "stats": {
                "id": {"value": identifier},
                "name": {"value": name},
                "source": {"value": "PHB"},
                "description": {"value": "Reference description"},
                "cost": {
                    "value": {
                        "stats": {
                            "value": {"value": 12},
                            "unit": {"value": "gold"},
                        }
                    }
                },
                "weight": {
                    "value": {
                        "stats": {
                            "value": {"value": 3},
                            "unit": {"value": "lb"},
                        }
                    }
                },
                "rarity": {"value": "common"},
                "is_magic": {"value": False},
                "requires_attunement": {"value": False},
            },
        }
        path = (
            root / "systems" / system / "resource_instances" / f"{identifier}.rpg.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def test_rpg_import_creates_distinct_sources_and_normalises_equipment(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = self._write_rpg_resource(root, "5e", "weapon", "sword", "Sword")
            self._write_rpg_resource(root, "5e2024", "weapon", "sword", "Sword")

            repository = CompendiumRepository.objects.get(identifier="default")
            source_2014 = CompendiumSource.objects.create(
                repository=repository, identifier="5e", name="5e"
            )
            source_2024 = CompendiumSource.objects.create(
                repository=repository, identifier="5e2024", name="5e2024"
            )
            self.assertEqual(
                import_rpg(root / "systems" / "5e", source_2014), (1, 0, 0)
            )
            self.assertEqual(
                import_rpg(root / "systems" / "5e2024", source_2024), (1, 0, 0)
            )

        sources = {
            source.identifier: source for source in CompendiumSource.objects.all()
        }
        entries = CompendiumEntry.objects.filter(name="Sword")
        self.assertEqual(entries.count(), 2)
        entry = entries.get(source=sources["5e"])
        self.assertEqual(entry.cost_amount, 12)
        self.assertEqual(entry.cost_currency, "gp")
        self.assertEqual(entry.weight_amount, 3)
        self.assertEqual(entry.weight_unit, "lb")
        self.assertEqual(entry.data, payload)
