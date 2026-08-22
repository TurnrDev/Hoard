# Compendium repositories and sources

The Compendium is Hoard's single catalogue of items, armour, weapons, spells,
feats, classes, races, backgrounds, and other reference entries. A campaign
uses only the sources it has enabled; there is no separate item-source setting.

The repository directory is the RPG Companion community registry. Each record
there is a `CompendiumRepository`; a repository can contain one or more
`CompendiumSource` collections, and each source contains Compendium entries.

## Custom content

Any campaign member can add custom items. Hoard stores them in a
campaign-owned repository and source, so they never become global catalogue content.
Campaign GMs manage changes and removal; imported entries remain read-only.

## RPG Companion community directory

Download the upstream archive and import it:

```sh
uv run python manage.py update_compendium_registries
```

The command fetches the canonical community directory, synchronises its
repository records, and imports the `5e` and `5e2024` sources from the
`default` repository. It is idempotent: running it again updates
entries by source identifier and adds newly available entries.

Use `--source /path/to/checkout` to import a deliberate checkout for that
same `default` repository instead of downloading its Git archive.

## Enable sources for a campaign

Importing a repository makes its sources available to Hoard; it does not
automatically expose them to every campaign. Game masters enable sources in
the Compendium screen.

The 5e Companion App remains supported for `.cah` character imports only; its
legacy catalogue is intentionally not bundled.

## Community repositories

Campaign GMs manage sources in the Compendium screen. The main discovery source
is the RPG Companion community registry at
`https://raw.githubusercontent.com/blastervla/rpg-companion-community-registry/master/registry.json`.
Hoard only lists compatible 5e and 5e2024 records there. The Compendium UI
only imports repositories discovered from this registry: it does not accept
arbitrary Git URLs, archive URLs, or uploaded archives. This keeps installed
sources attributable to a discoverable registry record.
