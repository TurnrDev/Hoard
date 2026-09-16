# Changelog

All notable changes to Hoard are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Hoard adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Restored calculated character statistics for hit points, initiative, proficiency,
  abilities, saving throws, and skills, with labelled calculation breakdowns.
- Added editable rolled, ancestry, background, and custom ability components;
  proficiency and custom skill/save adjustments; and separate Jack of All Trades and
  Remarkable Athlete options with their correct half-proficiency rounding rules.
- Restored current and temporary HP tracking, audited damage and healing, short rests
  that apply entered Hit Die recovery, and long rests that restore maximum HP. Both
  rest types now clear temporary HP.
- Added party-rail HP bars and initiative ordering for active encounters.

### Changed

- Improved the give coins the UI on the GM screen
- Restored the historical calculation cards, ability cards, proficiency picker, HP
  controls, and skill/save presentation on character profiles. Armor Class remains a
  blocked **Coming soon** card.
- Character profile edits and health changes now use validated WebSocket commands and
  authoritative events so connected clients refresh from the same state.

## [0.1.0] - 2026-09-16

### Added

- Shared campaign XP for active player characters, including level progress,
  remainder handling, reversals, and immutable ledger entries.
- Personal and campaign coin accounts with grants, spending, transfers, exact-value
  exchanges, reversals, and denomination-aware display.
- Campaign calendar management with in-world dates captured on audit and ledger
  events.
- Editable player-character and NPC profiles with portrait uploads, free-text race
  and class, personal money, and recent activity.
- Campaign membership, shareable invitations, roster management, and GM controls.
- Authenticated WebSocket queries, commands, events, and live campaign refreshes.
- Responsive desktop side rails, mobile campaign navigation, party switching, theme
  controls, and release-version display.
- Docker Compose development and production deployments using Daphne, Celery,
  PostgreSQL, Redis, Vite, and Nginx.
- A no-cache release manifest that prompts connected clients to refresh after a new
  version is deployed.

### Changed

- Reduced the character model to the profile data required by the initial release.
- Preserved the original character-sheet presentation as individually blocked
  **Coming soon** previews with skeleton values and explanatory copy.
- Merged campaign audit history and ledger infrastructure around the same immutable
  event model.
- Made shared XP the campaign default and excluded NPCs from XP distribution.
- Simplified campaign management and the GM dashboard around calendar, money, XP,
  roster, invitations, and ledger workflows.
- Made uploaded media publicly available through Nginx alongside static assets.
- Consolidated runtime configuration in the root `.env` file.

### Removed

- Compendium pages, routes, data access, build tasks, and repository dependencies;
  navigation retains a disabled **Coming soon** entry.
- Character import, builder, and level-up routes from the initial release UI.
- Deferred inventory, combat, health, rest, progression, and full character-sheet
  APIs and persistence.
- Support for upgrading pre-release databases; `0.1.0` starts from a clean initial
  migration.
