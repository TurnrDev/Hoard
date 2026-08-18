# Item catalogue

Hoard has two kinds of inventory item definition:

- **Global source items** are imported from the pinned `vendor/rpg-companion-app-systems` Git submodule. Hoard currently imports the `5e` and `5e2024` item resources only.
- **Campaign custom items** belong to one campaign. Any campaign member can create one; it is shared with the campaign and records the creating player. A GM can make an editable campaign copy of an imported item for house rules.

Initialise the source after cloning Hoard, then import or refresh it:

```sh
git submodule update --init --recursive
uv run python manage.py import_rpg_companion_items
```

The importer is idempotent. To update upstream content, update the submodule deliberately, review the new revision, then run the command again.

The upstream resource files are creative content licensed under CC BY-NC-SA 4.0. Hoard keeps the repository URL, system, source identifier, and original JSON on each imported item for attribution and traceability. See the [upstream repository](https://github.com/blastervla/rpg-companion-app-systems) for its current licence and source material.
