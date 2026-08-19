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
    def _write_item(
        self, directory: Path, system: str, identifier: str, name: str, resource_id: str = 'item'
    ) -> None:
        resource_directory = directory / 'systems' / system / 'resource_instances'
        resource_directory.mkdir(parents=True, exist_ok=True)
        (resource_directory / f'{resource_id}_{identifier}.rpg.json').write_text(json.dumps({
            'resource_id': resource_id,
            'stats': {
                'id': identifier,
                'name': {'value': name},
                'description': {'value': f'{name} description'},
                'source': {'value': 'dmg'},
                'type': {'value': 'shield' if resource_id == 'armor' else 'sword'},
                'rarity': {'value': 'rare'},
                'is_magic': {'value': True},
                'requires_attunement': {'value': False},
                'cost': {'value': {'resource_id': 'cost', 'stats': {'value': {'value': 15}, 'unit': {'value': 'gold'}}}},
                'weight': {'value': {'resource_id': 'weight', 'stats': {'value': {'value': 6.5}, 'unit': {'value': 'pounds'}}}},
            },
        }), encoding='utf-8')

    def test_import_is_idempotent_and_global_items_are_usable(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory)
            self._write_item(source, '5e', 'torch', 'Torch')
            self._write_item(source, '5e2024', 'torch', 'Torch (2024)')
            self._write_item(source, '5e', 'torch', 'Torch weapon', resource_id='weapon')
            self._write_item(source, '5e2024', 'shield', 'Shield', resource_id='armor')
            legacy = InventoryItem.objects.create(
                campaign=None,
                name='Old Torch',
                source_repository='https://github.com/blastervla/rpg-companion-app-systems',
                source_system='5e',
                source_identifier='torch',
            )
            call_command('import_rpg_companion_items', source=source)
            call_command('import_rpg_companion_items', source=source)

        self.assertEqual(InventoryItem.objects.count(), 4)
        item = InventoryItem.objects.get(source_system='5e', source_identifier='torch', equipment_category='item')
        self.assertEqual(item.pk, legacy.pk)
        self.assertIsNone(item.campaign)
        self.assertTrue(item.is_imported)
        self.assertEqual(item.equipment_category, 'item')
        self.assertEqual(str(item.cost_amount), '15.00')
        self.assertEqual(item.cost_currency, 'gp')
        self.assertEqual(str(item.weight_amount), '6.500')
        self.assertEqual(item.weight_unit, 'pounds')
        self.assertEqual(item.source_book, 'dmg')
        self.assertEqual(item.rarity, 'rare')
        self.assertTrue(item.is_magic)
        self.assertFalse(item.requires_attunement)
        self.assertEqual(
            InventoryItem.objects.get(source_system='5e', source_identifier='torch', equipment_category='weapon').name,
            'Torch weapon',
        )
        campaign = Campaign.objects.create(name='Hoard')
        character = make_character(campaign)
        grant_loot(recipient=character, item=item, quantity=1)
        self.assertEqual(character.inventory[item], 1)
