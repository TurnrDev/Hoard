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

Compile and import Hoard's embedded default fork, then refresh the community
registry:

```sh
uv run python manage.py update_compendium_registries
```

The command synchronises the canonical community directory when it is
available, then compiles and imports `5e` and `5e2024` from the upstream-history
fork in `hoard/compendium/systems/default`. It uses the official compiler under
`hoard/compendium/native/tools` on Linux x86-64. Set
`RPG_COMPANION_COMPILER=/path/to/refresh_system_builder` to use the compiler
installed by the RPGScript VS Code extension on another platform.

Compiled packages are reproducible build artifacts in
`hoard/compendium/systems/compiled` and are intentionally ignored by Git. The
production Docker image creates them while building. The import command compiles
to a temporary directory, so local imports cannot leave stale executable
definitions behind. It remains usable offline when the default repository has
already been seeded. It is idempotent: running it again updates entries by
native source identifier, removes stale imported entries, and adds newly
available entries.

The Debian image sets `HOARD_USE_COMPILED_SYSTEMS=true` and runs
`update_compendium_registries --no-registry --if-missing` after migrations.
Consequently, a fresh deployment seeds its build-time packages without network
access, while an existing database starts without recompiling or reimporting.

Use `--source /path/to/checkout` to compile and import a deliberate checkout for that
same `default` repository. Use `--remote` to deliberately download and import
the registry's current default release instead of the bundled fork.

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
