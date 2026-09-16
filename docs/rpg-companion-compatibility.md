# RPG Companion compatibility architecture

Hoard is a native host for the RPG Companion `5e` and `5e2024` systems. It
embeds a history-preserving fork of the open systems repository at
`hoard/compendium/systems/default/` and compiles that source during the Docker
build. Generated packages under `hoard/compendium/systems/compiled/` are build
artefacts and are deliberately not committed.

## The hybrid state model

Native RPG Companion state is authoritative. Hoard also keeps selected Django
columns and relationships as transactional read projections because they make
the ledger, party overview, group experience, combat, and existing reports
efficient and reliable.

The invariant is one-way:

1. A WebSocket command is validated and translated into a native event.
2. The interpreter runs system and resource mechanics atomically.
3. Native state and an immutable `CharacterNativeEvent` audit record are saved.
4. Hoard projections are derived from the resulting state in the same transaction.
5. A campaign event tells every connected client to query the new state.

Projection fields must never be edited independently. Legacy commands are
adapters into this flow, not a second rules engine. A failed mechanic,
projection, or database write rolls back the complete operation.

Hoard's append-only money, inventory, experience, and health ledgers remain
authoritative domain event streams rather than editable projections. Their
current balances and selected resources are materialised into native scope; a
ledger command and its corresponding native event/projection execute in one
transaction where the native system owns that state (for example group XP and
health). This preserves reversal and audit guarantees without inventing a second
editable copy of a balance.

The direct `Character.spells` many-to-many relationship records selection only.
Spell definitions live exclusively in `CompendiumEntry.data`. Preparation and
character-owned spell snapshots do not exist.

## 5e and 5e2024 lineage

The two systems retain their upstream IDs and are treated as one compatible
resource family. Neutral content such as spells, items, feats, backgrounds,
species/races, and creatures can be mixed when its source is enabled.

A character chooses `5e` or `5e2024` as its starting rules lineage. Once a class
has been selected, class and subclass choices remain on that exact lineage.
This prevents a resource mix from silently combining different class progression
engines. The builder and level-up screens enforce and explain the restriction.

The campaign stores its baseline source/version. A source supplying the campaign
baseline or an active character cannot be disabled until a replacement is chosen.

## Compendium and custom content

Every imported native resource type is retained, including kinds Hoard does not
have a dedicated model for. The Compendium browser searches all enabled kinds.
Known 5e content receives dedicated cards; extension content remains available
to the generic native renderer.

Any character editor can create a campaign-custom spell. Editing published
content always clones it and atomically switches the current character to the
clone. Editing campaign-custom content explicitly offers a shared update or a
clone for the current character. Detaching never deletes Compendium content.

The custom-content export produces a published-repository ZIP containing a
`systems.rpg` manifest, the complete active system plus Hoard overlay as
`<system>/system.rpg`, and a compatible `<system>/resources.rpg.gzip`. The
resource pack is an outer gzip-compressed tar with individually gzip-compressed
`.rpg` instances under `resources/`. It contains campaign-custom resources only,
never third-party source entries; the system definition retains the applicable
upstream licence.

## CAH import matching

CAH spell records are normalised to the canonical spell card while the
server-side draft retains the original record. Resolution order is:

1. one enabled entry with the exact source identifier;
2. one enabled entry with the exact or normalised name;
3. explicit selection or creation of a prefilled campaign-custom spell.

Ambiguous matches are never guessed. If spells are included, commit is blocked
until every row has an enabled selection. The complete spells collection may be
excluded instead.

## Native interpreter and views

The interpreter evaluates compiled formulas, base/calculated stats, resource
scopes, event cascades, reversible value and modifier overrides, conflict
aggregation, rolls, interface effects, and delayed effects. Delayed work is
persisted and executed by Celery. Every execution records messages, changes,
interface actions, unsupported nodes, source version, and package checksum.

Hoard purpose-builds common sheet sections and uses native ordering plus a
recursive renderer for extensions. Native controls use the same WebSocket event
path as dedicated controls. A “System behaviour” disclosure identifies their
event; unsupported behavior is warned about rather than silently omitted.

## Compiler, licences, and provenance

The embedded content keeps its upstream history, IDs, and `LICENSE.md`. That
authoritative file declares CC BY-NC 4.0. The upstream README currently mentions
CC BY-NC-SA 4.0; Hoard preserves and documents this discrepancy rather than
rewriting it. Distribution must comply with the upstream content licence.

The Linux x86-64 compiler and schema come from the MIT-licensed RPGScript VS Code
extension. Their separate notice and provenance live in
`hoard/compendium/native/tools/`. The compiler licence does not change the
licence of compiled game-system content.

## Refreshing the embedded fork

Do not replace the directory with a copied archive. Fetch upstream and merge its
history into Hoard, resolving changes under `hoard/compendium/systems/default/`
while retaining IDs and licences. The initial import used
`git merge --allow-unrelated-histories`; later refreshes merge the recorded
upstream history normally.

After a refresh:

1. inspect upstream licence and README changes;
2. run the embedded repository validation without formatting generated content;
3. run `docker compose build` to regenerate both systems with the official compiler;
4. run ingestion/interpreter fixtures for `5e`, `5e2024`, and an extension pack;
5. verify source IDs and package checksums before deployment.

The published Obojima core-set repository was also exercised directly at commit
`698ab7080a77a86464178a0cccd61539ba543071`: Hoard read its `5e` 0.6.0 manifest,
system definition, and nested compressed resource archive, importing 77 resource
instances in a rolled-back compatibility check. No Obojima content is vendored by
that check.

## Authoring extensions

Develop extensions in the RPG Companion repository layout, preferably using
`.rpgs` source and the RPGScript VS Code extension for diagnostics. Keep resource
and system IDs stable: Hoard uses the native ID as its first match key and only
falls back to a unique normalised name.

A resource instance must name its native definition and contain wrapped native
stats, for example:

```json
{
  "resource_id": "spell",
  "stats": {
    "id": { "value": "my-pack:spell:wind-step" },
    "name": { "value": "Wind Step" },
    "level": { "value": "spell_level_2" },
    "description": { "value": "Your extension description." }
  }
}
```

Put development instances in `systems/5e/resource_instances/` or
`systems/5e2024/resource_instances/`. Neutral content may be supplied for either
lineage; class and subclass definitions must remain with the exact system they
extend. Use native views and mechanics rather than Hoard-only fields. Hoard's
generic renderer implements every view primitive in the vendored schema and
will display an explicit warning for a future primitive it does not yet know.

Compile with `refresh_system_builder --base=<systems-dir> --output=<output-dir>
--clean --structured-diagnostics`, then import the published or development
repository through Compendium Sources. Test resource creation/removal events,
reversible effects, relevant rests, and both narrow/mobile and 200% zoom layouts.

## Development and deployment

Docker Compose is the preferred full-stack development environment and mirrors
the Debian production image:

```console
docker compose up --build
```

The Nix shell is a host-side contributor toolbox for Python 3.14, `uv`, Node 24,
Git, Docker 29, and Compose. It does not replace the container stack. See the
root README and `docs/compendium.md` for setup and import commands.
