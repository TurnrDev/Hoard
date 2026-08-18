from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hoard.campaigns.models import InventoryItem


SOURCE_REPOSITORY = 'https://github.com/blastervla/rpg-companion-app-systems'
SYSTEMS = ('5e', '5e2024')


def _stat_value(stats: dict[str, Any], name: str) -> object | None:
    value = stats.get(name)
    if isinstance(value, dict):
        return value.get('value')
    return value


class Command(BaseCommand):
    help = 'Import global 5e and 5e2024 item resources from rpg-companion-app-systems.'

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            '--source',
            type=Path,
            default=settings.BASE_DIR / 'vendor' / 'rpg-companion-app-systems',
            help='Path to the checked-out rpg-companion-app-systems repository.',
        )

    def handle(self, *args: object, **options: object) -> None:
        source = Path(options['source'])
        if not source.is_dir():
            raise CommandError(f'Item source directory does not exist: {source}')
        created = 0
        updated = 0
        skipped = 0
        for system in SYSTEMS:
            resource_directory = source / 'systems' / system / 'resource_instances'
            if not resource_directory.is_dir():
                raise CommandError(f'Missing resource directory for {system}: {resource_directory}')
            for path in resource_directory.glob('*.rpg.json'):
                try:
                    resource = json.loads(path.read_text(encoding='utf-8'))
                except json.JSONDecodeError as error:
                    raise CommandError(f'Invalid JSON in {path}: {error}') from error
                if resource.get('resource_id') != 'item':
                    continue
                stats = resource.get('stats')
                identifier = _stat_value(stats, 'id') if isinstance(stats, dict) else None
                name = _stat_value(stats, 'name') if isinstance(stats, dict) else None
                description = _stat_value(stats, 'description') if isinstance(stats, dict) else ''
                if not isinstance(identifier, str) or not isinstance(name, str) or not name:
                    skipped += 1
                    continue
                item, was_created = InventoryItem.objects.update_or_create(
                    source_repository=SOURCE_REPOSITORY,
                    source_system=system,
                    source_identifier=identifier,
                    defaults={
                        'campaign': None,
                        'created_by': None,
                        'name': name,
                        'description': description if isinstance(description, str) else '',
                        'source_data': resource,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Imported items: {created} created, {updated} updated, {skipped} skipped.'))
