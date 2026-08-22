# Equipment catalogue

Hoard imports global equipment from repositories discovered through the RPG
Companion community registry.
The importer supports `item`, `weapon`, and `armor` resources from both `5e`
and `5e2024`.

Each imported record preserves the complete upstream JSON for provenance and
also extracts facts useful to a DM and players: source book, category, type,
cost, weight, rarity, magic, and attunement. A missing fact means the upstream
resource did not provide a usable value; it is not treated as zero or false.

Synchronise the registry and install its default repository with:

```sh
uv run python manage.py update_compendium_registries
```

It upserts imported equipment by repository, source, equipment category, and
upstream identifier. Rerunning it updates facts without duplicating entries.

Campaign item source settings control which global systems appear in a
campaign. Campaign custom items are always available, and can record the same
facts as imported items. Costs are descriptive catalogue data only; granting,
spending, and exchanging money continue to use the ledger actions.

## Frontend picker

Every item action opens the same equipment picker. It searches names,
descriptions, sources, categories, and types, and filters system, source book,
category, type, rarity, magic, attunement, cost, and weight. Cost filters use
gold-piece equivalents; cards retain the original denomination.

For transfers and item removal, the picker only lists positive balances in the
chosen character’s inventory and displays the recorded quantity.
