from __future__ import annotations

import gzip
import io
import json
import tarfile
import zipfile

from django.test import TestCase

from hoard.campaigns.models import Campaign
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)
from hoard.compendium.native.export import (
    export_campaign_repository,
    export_campaign_resources,
)


class NativeResourceExportTests(TestCase):
    def test_exports_campaign_resources_in_published_package_shape(self) -> None:
        campaign = Campaign.objects.create(name="Export campaign")
        repository = CompendiumRepository.objects.create(
            identifier="campaign-export-custom",
            campaign=campaign,
            name="Custom content",
        )
        source = CompendiumSource.objects.create(
            repository=repository,
            identifier="custom",
            name="Custom content",
        )
        resource = {
            "resource_id": "spell",
            "stats": {
                "id": {"value": "custom:spell:test"},
                "name": {"value": "Test Spell"},
            },
        }
        CompendiumEntry.objects.create(
            source=source,
            kind=CompendiumEntry.Kind.SPELL,
            source_identifier="custom:spell:test",
            name="Test Spell",
            data=resource,
        )

        package = export_campaign_resources(campaign)

        with gzip.GzipFile(fileobj=io.BytesIO(package.content)) as compressed:
            with tarfile.open(fileobj=compressed, mode="r|") as archive:
                files = {
                    member.name: archive.extractfile(member).read()
                    for member in archive
                    if member.isfile()
                }
        encoded = files["resources/custom_spell_test.rpg"]
        self.assertEqual(json.loads(gzip.decompress(encoded)), resource)
        self.assertEqual(package.resource_count, 1)

        repository_package = export_campaign_repository(
            campaign,
            {
                "id": "5e",
                "name": "5e with Hoard",
                "version": "0.9.0",
                "character_stats": [{"id": "hoard_group_experience"}],
            },
        )
        with zipfile.ZipFile(io.BytesIO(repository_package.content)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"systems.rpg", "5e/system.rpg", "5e/resources.rpg.gzip"},
            )
            definition = json.loads(gzip.decompress(archive.read("5e/system.rpg")))
        self.assertEqual(definition["character_stats"][0]["id"], "hoard_group_experience")
