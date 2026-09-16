# Hoard 0.1.0: Minimal Campaign Release

## Summary

Create the first release on `release/0.1.0`, based on `main`. Keep the proven
campaign, calendar, invite, money, XP, audit, and ledger foundations; reduce
character profiles to identification and money/XP participation.

`develop` remains the source of all deferred compendium and full-sheet work.
The release branch does not retain commented-out implementation code.

## Retained domain model

- Keep `Campaign`, `CampaignContext`, `Character`, and `MoneyBalance`.
- Reduce `Character` to campaign/context ownership, `kind` (`pc` or `npc`),
  active state, name, portrait, free-text race, and free-text class.
- Remove `Campaign.use_shared_exp`; group XP is always shared among active
  PCs. NPCs are excluded.
- Keep `Campaign.shared_experience`, level thresholds, and campaign level.
- Keep money exactly as it exists: currency denominations and decimal/gold-value
  presentation; campaign system and character money accounts; balanced,
  immutable transactions and entries; grants, spending, equal-value exchanges,
  and reversals.
- Keep XP exactly as it exists: campaign system and character XP accounts;
  balanced immutable entries; active-character baselines, shared awards,
  discarded remainders, reversals, campaign XP, and level thresholds.
- Merge the abstract audit and ledger bases into one module because ledger
  transactions are campaign audit events. Retain immutable event behaviour,
  actor attribution, timestamps, in-world date snapshots, and ledger semantics.
- Keep invitations and invitation audit events, but simplify acceptance to
  create a blank inactive PC profile with no builder, health baseline, or
  character-history record.
- Keep campaign calendar and membership audit data.
- Remove inventory, combat, health, progression, character-sheet, CAH,
  native-system, and compendium models, services, and tasks.

## Application and UI

- Preserve existing money and XP WebSocket commands, queries, events,
  permission checks, and ledger presentation wherever they do not depend on
  removed features.
- Remove only inventory/compendium/import/health/combat/rest/builder/level-up
  commands and their payload contracts.
- Keep profile, roster, player rail, ledger, GM dashboard, calendar, campaign
  management, login, and shareable-invite flows.
- Replace the full character sheet with a simple editable profile showing
  portrait, name, race, class, PC/NPC type, personal coin pouch, group XP, and
  campaign level.
- Retain portrait upload and private authenticated portrait serving.
- Simplify the GM dashboard to calendar, party money, shared XP, coin
  awards/transfers, roster, invites, and ledger actions.
- Keep Compendium in the sidebar as a “Coming soon” destination; remove all
  compendium data access and management.
- Remove character-import controls and routes; show “Character import — coming
  soon.”
- Render deferred profile capabilities—detailed sheet, health, abilities,
  equipment, spells, rests, combat, and level-up—as labelled, non-interactive
  “Coming soon” panels using PrimeVue Skeleton placeholders. Their text conveys
  the state independently of colour or skeletons.
- Remove builder and level-up routes rather than leaving unreachable functional
  pages.

## Database, release, and deployment

- Delete existing project migrations and generate one clean initial migration
  for the retained release schema. Existing pre-release databases are
  intentionally unsupported and must be recreated.
- Remove the Compendium Django application, URLs, tasks, tests, frontend routes,
  build steps, and Docker dependencies from this branch.
- Add `Dockerfile`, `compose.dev.yml`, and `compose.prod.yml`:
  development uses source mounts, Vite live reload, Daphne, PostgreSQL, Redis,
  and persistent local volumes; production uses Daphne, Celery, PostgreSQL,
  Redis, and Nginx. Nginx serves static files and proxies authenticated media,
  HTTP, and WebSocket requests to Daphne.
- Production uses an internal named network for app/worker/database/Redis and
  the external `web` network for Nginx/Traefik, including Traefik labels.
- Use environment variables for non-sensitive configuration and Docker secrets
  for Django and database secrets.
- Remove compendium compilation and registry initialisation from the image and
  entrypoint.
- Document Docker as the supported full-stack developer workflow and update
  `shell.nix` accordingly.
- Set the canonical release version to `0.1.0`, use `version-bump` to update
  Python and frontend package metadata together, and add a Keep a Changelog
  `CHANGELOG.md`.
- Display the version in the application shell. Expose a no-cache release
  manifest; when the running deployment version changes, prompt for and perform
  a client refresh.

## Verification

- Test money and XP system-account creation, balancing, denominations, decimal
  values, active-PC distribution, NPC exclusion, remainder handling, activation
  baseline, and reversals.
- Test audit/ledger immutability, actor attribution, and campaign-date
  snapshotting after the module consolidation.
- Test minimal PC/NPC creation, profile updates, portrait permissions, calendar
  adjustment, shareable invitation acceptance, GM permissions, and player rail
  data.
- Test that compendium/import/health/combat/builder/level-up APIs are absent and
  their UI is visibly “Coming soon.”
- Run Ruff for `hoard`, `npm run fix`, the frontend build, clean migration
  checks, and the focused backend test suite.
- Verify development and production Compose builds, static delivery,
  authenticated portrait delivery, WebSocket proxying, and production
  network/Traefik configuration.

## Assumptions

- `0.1.0` is intentionally pre-1.0 and may make breaking changes.
- The release database starts empty.
- No email invitation delivery is included; invites are shareable links.
- Future implementation belongs on `develop`, not as commented code in the
  release branch.
