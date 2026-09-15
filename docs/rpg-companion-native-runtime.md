# Hoard-native RPG Companion 5e runtime

## Summary

Turn Hoard into a compatible host for the upstream `5e` and `5e2024` RPG
Companion systems, using a Hoard-maintained fork in this repository as the
default source. Native state, formulas, mechanics, effects, and events are
authoritative; existing Hoard features become transactional projections and
enhanced UI renderers.

## Repository and package model

- Add the upstream Open Systems Repository under `hoard/compendium/systems/`
  through a documented merge with unrelated histories; retain upstream `5e`
  and `5e2024` IDs and the CC BY-NC-SA 4.0 content licence.
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
