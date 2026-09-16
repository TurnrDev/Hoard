# Hoard-native RPG Companion 5e runtime

## Summary

Turn Hoard into a compatible host for the upstream `5e` and `5e2024` RPG
Companion systems, using a Hoard-maintained fork in this repository as the
default source. Native state, formulas, mechanics, effects, and events are
authoritative; existing Hoard features become transactional projections and
enhanced UI renderers.

## Implementation status

This document is the durable execution checklist for the migration. A checked
item is implemented and verified; unchecked items remain required before the
native-runtime project is complete.

- [x] Replace character-owned spell records with a direct
  `Character.spells` many-to-many relationship to compendium entries.
- [x] Merge the upstream systems repository with unrelated histories and retain
  its upstream commit history and IDs under `hoard/compendium/systems/default/`.
- [x] Treat compiled 5e and 5e2024 packages as reproducible build artefacts;
  build them from the embedded source fork with the vendored compiler rather
  than committing generated packages.
- [x] Vendor the official Linux x86-64 RPGScript compiler and schema from the
  RPGScript VS Code extension with its MIT notice and provenance.
- [x] Add a Debian production container path for the web app, worker, database,
  Redis, frontend assets, and native compiler.
- [x] Store complete native system definitions, package versions, minimum app
  versions, layouts, checksums, and arbitrary native resource types.
- [x] Compile `.rpgs` development repositories with the official compiler before
  import; retain lossless JSON composition for JSON-only fixtures.
- [x] Finish and verify the complete formula/mechanic/effect interpreter,
  including resource mechanics, reversible effects, lifecycle events, delayed
  execution, dice semantics, and every node used by supported systems.
- [ ] Make native character state authoritative for every character domain,
  including RPG Companion class-details and level-up state, and route every
  legacy mutation through transactional interpreter/projection adapters.
- [x] Enforce baseline-system lineage rules while allowing compatible neutral
  5e/5e2024 resources.
- [x] Complete native spell create, attach, detach, cast, shared update, and
  clone-and-switch workflows.
- [x] Complete CAH spell resolution by source ID and normalized-name fallback,
  with explicit ambiguity resolution and commit blocking.
- [x] Implement the Hoard-styled generic native view renderer and dedicated core
  renderers, including visible system-behaviour diagnostics.
- [x] Implement compatible custom-resource and Hoard-overlay export.
- [ ] Complete upstream/Obojima compatibility verification, backend/frontend
  tests, Ruff, frontend formatting, and the production container build after
  the native class-details migration.
- [ ] Complete hands-on accessibility verification with a browser and assistive
  technology: keyboard focus, 200% zoom/reflow, contrast, red/green
  colour-vision simulation, and affected views with a screen reader. This
  requires a graphical browser session that is not available in the current
  workspace; the semantic/source-level review and automated build checks pass.
- [x] Finish the architecture, compatibility, extension-authoring, licensing,
  and upstream-refresh documentation.

Historical verification before the class-details correction: the schema
conformance test covers every formula, effect, and view primitive in the
vendored official schema; both compiled default system definitions report no
unsupported node types. The complete backend suite (110 tests), frontend suite
(28 tests), frontend production build, and Debian app and worker image build
passed. A clean container database applied every migration, imported 5,477
native entries, and passed Django's system check. The real Obojima published
package at commit `698ab7080a77a86464178a0cccd61539ba543071` imported 77
entries in a rolled-back compatibility check. These results must be repeated
after the work below.

## Active correctness remediation: classes, levels, and CAH jobs

The first native-runtime implementation incorrectly persisted a
`CharacterClassLevel` row for every total character level and rebuilt the
native `classes` stat from those rows on each event. That is not the RPG
Companion data model and overwrites native class state. In particular, it loses
the per-class level, selected archetype, and selected feature IDs in a CAH
character's `jobs` collection.

The replacement work is in progress and has these non-negotiable outcomes:

- Character class state is one native `class_details` resource per class. Its
  `class_level`, `archetype_id`, and selected-feature state are authoritative.
- Linked Compendium class entries supply immutable native class definitions;
  the class-details wrapper remains character state and is never regenerated
  from rows on unrelated commands.
- Character level is the upstream calculated sum of all class-details levels.
  Campaign level remains Hoard's group-XP target and completion gate only.
- CAH `jobs` resolve class IDs and subtype IDs to enabled native Compendium
  entries, preserve multiclass levels, and block the included classes
  collection until each job is resolved or created as campaign-custom content.
- The builder and level-up UI use class resources directly. The old
  `CharacterClassLevel`, `CharacterLevelProgress`, per-level allocation UI,
  and hand-maintained spell-slot/class calculations are removed.

### Implemented in this pass

- `CharacterClassLevel`, `CharacterLevelProgress`, and character-owned class
  choices are removed by migration `0023`; selected classes are represented by
  native `class_details` resources and linked class Compendium entries.
- A character's level is the sum of native class-detail levels. Campaign level
  is a group progression target, not a second character-level authority.
- CAH jobs now parse as class, level, subclass, and feature-selection records.
  The import preview resolves each class by native source ID or unique name,
  lets the user search the enabled lineage, and blocks only the included
  Classes collection until every class is resolved.
- Nested resource paths in the interpreter now resolve calculated resource
  stats, not only stored values. This is required by the upstream 5e
  `long_rest` mechanic when it reads class caster-level and per-level slot
  definitions.
- Spell-slot maxima, current values, and per-class spell attack/save values are
  now projected from native state and native event previews. The former
  hand-maintained full-, half-, third-, and pact-caster tables are gone.
  Long Rest delegates HP, Hit Dice, and spell-slot restoration to the native
  `long_rest` event; Hoard only clears its own temporary-HP extension.

## Repository and package model

- Add the upstream Open Systems Repository under `hoard/compendium/systems/`
  through a documented merge with unrelated histories; retain upstream `5e`
  and `5e2024` IDs and the licence supplied with the content. The embedded
  repository's authoritative `LICENSE.md` declares CC BY-NC 4.0; its README
  currently mentions CC BY-NC-SA 4.0, and that upstream discrepancy must remain
  visible in Hoard's licensing documentation rather than being silently
  reconciled.
- Maintain Hoard changes as a clearly separated native-system overlay/fork:
  group XP, ledger integration, campaign features, and Hoard-specific
  views/mechanics.
- Support both native development layouts (including split `system/`, `.rpgs`,
  and `resource_instances/`) and published package layouts. Implement the
  documented composition and merge rules rather than treating resource files
  as standalone entries.
- Preserve complete native system definitions and resource instances with
  stable IDs, version/provenance metadata, and refresh semantics.

## Runtime and campaign state

- Add a native-system baseline to campaigns, with `5e` and `5e2024`
  interoperable for neutral resources but class/subclass lineage locked to the
  character's chosen baseline.
- Implement the full native interpreter: stat formulas, base/computed values,
  overrides and aggregation, events, mechanics, reversible effects, lifecycle
  events, delayed actions, and resource relationships.
- Make native state authoritative. Persist current Hoard fields as
  transactional read projections for query performance and existing services;
  native events are the only mutation route.
- Adapt existing Hoard commands into native-event adapters and emit the
  existing WebSocket events after interpreter execution and projection updates.
- Replace the incomplete current spell work with direct character-to-native-
  resource relationships and native spell mechanics.

## Hoard-styled native UI

- Use one Hoard-styled character sheet whose section ordering comes from the
  native system definition.
- Render known core 5e sections with purpose-built Hoard components: summary,
  abilities, inventory, spells, combat, progression, group XP, and ledger.
- Build a generic native renderer for all remaining sections and extension
  resources, mapping native view semantics to the existing Bootstrap/PrimeVue
  theme and accessibility patterns.
- Support the documented native view primitives, editing controls, resource
  selectors, pop-ups, and event buttons. Native layout hints inform rendering;
  Hoard controls colour, contrast, typography, responsive behaviour, focus,
  and reduced-motion treatment.
- Include a contextual “System behaviour” disclosure for native controls,
  showing the event, mechanics, effects, and resulting changes. Unsupported
  native behaviour is shown clearly rather than omitted.

## Compatibility and verification

- Rework compendium import/search/CAH matching to use native IDs first and
  normalized names only as fallback.
- Export campaign-custom resources and the Hoard overlay as valid native
  resource/system content.
- Add upstream 5e, 5e2024, and Obojima fixtures for package composition,
  resource imports, interpreter execution, view rendering, custom overlays,
  mixed-resource restrictions, and export compatibility.
- Test projection consistency, effect reversion/conflicts, event audit history,
  group XP integration, accessibility of generic views, and upstream-fork
  refreshes.
- Document architecture, native-state/projection invariants, fork
  sync/licensing process, supported native contract, and extension-authoring
  guide.

## Decisions

- Full interpreter compatibility is required for the supported systems.
- Both `5e` and `5e2024` retain their upstream identifiers and are supported.
- Characters may use compatible neutral resources across systems, but their
  class and subclass lineage remains tied to their starting system.
- Native state is authoritative; Hoard fields are read projections and are not
  independently writable.
- The upstream fork lives in this repository and remains compatible with RPG
  Companion release formats.
- Hoard has one styled sheet: known sections receive custom renderers and all
  other native views use the generic renderer.
- The official RPGScript compiler tooling is distributed under MIT separately
  from system/resource content. Hoard vendors the Linux x86-64 tool for its
  Debian image and accepts `RPG_COMPANION_COMPILER` as an explicit override for
  extension-installed or other platform builds.
