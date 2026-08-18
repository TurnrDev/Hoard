from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from hoard.campaigns.models import Campaign, InventoryItem
from hoard.campaigns.services import grant_loot

from .helpers import make_character


class RpgCompanionImportTests(TestCase):
    def _write_item(self, directory: Path, system: str, identifier: str, name: str) -> None:
        resource_directory = directory / 'systems' / system / 'resource_instances'
        resource_directory.mkdir(parents=True)
        (resource_directory / f'item_{identifier}.rpg.json').write_text(json.dumps({
            'resource_id': 'item',
            'stats': {
                'id': identifier,
                'name': {'value': name},
                'description': {'value': f'{name} description'},
            },
        }), encoding='utf-8')

    def test_import_is_idempotent_and_global_items_are_usable(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory)
            self._write_item(source, '5e', 'torch', 'Torch')
            self._write_item(source, '5e2024', 'torch', 'Torch (2024)')
            call_command('import_rpg_companion_items', source=source)
            call_command('import_rpg_companion_items', source=source)

        self.assertEqual(InventoryItem.objects.count(), 2)
        item = InventoryItem.objects.get(source_system='5e', source_identifier='torch')
        self.assertIsNone(item.campaign)
        self.assertTrue(item.is_imported)
        campaign = Campaign.objects.create(name='Hoard')
        character = make_character(campaign)
        grant_loot(recipient=character, item=item, quantity=1)
        self.assertEqual(character.inventory[item], 1)
