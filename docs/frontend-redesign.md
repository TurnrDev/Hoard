# Hoard frontend redesign

## Status

This is the living design record for the fresh Hoard frontend. Update it whenever
we make a design decision or identify an open question.

The previous Vuetify-to-PrimeVue conversion approach is superseded. Existing UI
implementation is disposable; existing application behaviour, routes, WebSocket
queries and commands, realtime events, and permission rules are not.

## Foundation

- Use Vue 3 with the Options API.
- Order Vue single-file components as `<template>`, then `<script lang="ts">`,
  then any `<style>` block. Keep this order for all fresh and rebuilt files.
- Use PrimeVue 4, with local component imports. Do not globally register,
  alias, or wrap PrimeVue components.
- Keep PrimeVue's native local component names (`Button`, `Dialog`, `Select`,
  `Textarea`, and so on). Do not rename them to `PrimeButton`-style aliases.
- Remove PrimeVue 5 and the PrimeUI licence-manager integration.
- Use the PrimeVue 4 Lara preset as the component starting point. Lara is the
  Bootstrap-based built-in preset and therefore aligns with Hoard's
  Bootstrap-first layout approach.
- Define a small Hoard preset from Lara using PrimeVue theme tokens for
  component-level colour and surface changes. Keep Bootstrap and Hoard SCSS
  variables aligned with those token decisions.
- Use Bootstrap wherever it supplies an appropriate layout, responsive grid,
  spacing, display, sizing, or accessibility utility. Prefer it over custom CSS
  for ordinary layout and presentation.
- Keep custom CSS small and Hoard-specific: application identity, component
  exceptions, and behaviour Bootstrap does not provide. Do not introduce another
  layout or utility framework.
- Use Bootstrap's CSS variables and colour utilities, plus PrimeVue theme tokens, before adding Hoard-specific CSS variables. Add a custom variable only when neither framework expresses the
  needed semantic value.
- Keep MDI icons. Every icon-only control needs an accessible name.
- The visual direction is Hoard's dark tabletop identity, informed by the old
  v0 product patterns and 5e Companion interaction ideas, without copying either.
- In the Normal palette, green is the primary interaction colour. Parchment gold
  is an accent for tabletop identity, focus, and selected emphasis; it is not the
  default fill for every action button.
- The Hoard wordmark remains parchment gold in every palette. The favicon uses
  the same gold coin-and-H mark and adapts its background to the browser's light
  or dark colour preference.

### Colour mode

- Support light and dark colour modes with a user-operated selector in the
  application shell.
- Use PrimeVue's class-based dark mode selector at the document root rather than
  relying only on the operating-system preference.
- The selector should offer Light, Dark, and System. System is the initial
  default for a new user; an explicit choice persists locally and is applied
  before the application renders to avoid a theme flash.
- The appearance menu presents those modes as System, Parchment, and Midnight,
  and presents the Normal and Melly-vision palettes as Hoard and Melly. These
  are display labels only; the stored preference values remain stable.
- Colour mode and palette are nested submenus in the top-right account menu so
  appearance preferences do not permanently consume header space or create
  competing select overlays inside another popup.
- The selected colour mode changes both PrimeVue tokens and Bootstrap/application
  CSS variables.
- Both modes must meet the same contrast and non-colour state requirements.
- Light mode uses a muted `#eee6d5` parchment canvas rather than a bright white
  application background, keeping the overall brightness closer to a printed
  character sheet.
- The header, campaign navigation, and Party Rail share Bootstrap's tertiary
  background as a single shell-chrome surface. The main content uses the body
  background, with a subtle contrast between chrome and content in both modes.
- Support two independently selectable colour palettes in both light and dark
  mode: Normal and Melly-vision. Melly-vision is the red–green colourblind
  friendly palette and also serves as a low-glare option for Melly's
  astigmatism.
- The Normal palette may use familiar green and grey status colours, and
  red/orange/yellow health colours.
- Melly-vision uses distinguishable blue, pink, and yellow variations for
  equivalent state categories. In dark mode it must avoid pure or near-white
  text directly against near-black surfaces; use subdued warm-grey foreground
  steps while retaining WCAG 2.2 AA contrast.
- Normal dark mode uses the warm `#d8d2c7` parchment-grey foreground to reduce
  glare. Melly-vision retains its dimmer low-glare foreground. Both palettes use
  coordinated Hoard, Bootstrap, and PrimeVue foreground tokens.
- Use icons, symbols, text, ordering, and patterns wherever sensible so palette
  selection improves recognition rather than becoming the only accessibility
  mechanism.

## Component approach

Use components generously where they represent a meaningful UI concept, repeated
pattern, interaction, or unit of state. Do not preserve old component boundaries
when they obstruct the new design.

Candidate shared components include AppShell, CampaignHeader, CampaignNavigation,
PartyRail, GameMasterPresence, PartyRoster, PartyRailMember, InitiativeTracker,
InitiativeCombatant, CombatantVisibilityControls, and character sheet sections
such as ability scores, resources, inventory, and activity.

The PartyRail component tree is deliberate:

```
PartyRail
├── GameMasterPresence
├── PartyRoster (out of combat)
│   └── PartyRailMember
│       └── PartyRailEntry
└── InitiativeTracker (in combat)
    └── InitiativeCombatant
        ├── PartyRailEntry
        └── CombatantVisibilityControls (GM only)
```

PartyRail is global campaign chrome. It is owned by AppShell and remains
available across campaign routes rather than being mounted only by Play or GM
pages. Its content changes between the out-of-combat party roster and the
in-combat initiative tracker.

The initial `campaign.get` WebSocket query supplies the safe member identity data
needed by PartyRail as well as the visible characters and campaign state. The
shell must not depend on the GM-only campaign-management member query to render
the rail for a player context.

On desktop, PartyRail is narrow by default and can expand without navigating
away from the current page. The compact rail keeps each token/avatar, status
icon, and concise HP state visible. The expanded rail adds names, HP numbers,
condition names/details, and GM-only combat controls. Initiative values are
available only within those GM controls and are not displayed on rail entries.
Use a visible labelled toggle with aria-expanded state; it must be
keyboard-operable and must not depend on hover.

## Application shell

AppShell is persistent campaign chrome. Route navigation replaces only the main
workspace; campaign context, navigation, and PartyRail stay available.

### Desktop

The shell has three columns below the campaign header:

1. Campaign navigation
   - Persistent route navigation: Play, Characters, Compendium, Ledger, and
     GM-only management routes.

2. Main workspace
   - The routed page content.
   - Play renders the full playable character sheet.
   - GM renders campaign controls and the encounter workspace.
   - Builder, compendium, and ledger use the available workspace width without
     mounting a second roster.

3. Global PartyRail
   - Compact by default. It is a narrow vertical sequence of avatars/tokens with
     OverlayBadges, compact HP bars, and condition icons. During combat, the same
     entries are sorted into initiative order without exposing initiative values.
   - The GM is always first and visibly separated from players/combatants.
   - Expanding the rail widens the application-shell column and correspondingly
     reflows the main workspace; it does not open a floating overlay.
   - The expanded rail reveals character names, explicit HP values, condition
     details, and GM-only combatant visibility controls.

The header contains the Hoard identity, campaign and current in-world date,
colour mode and palette controls, and the account menu.
For a PC context, the account-menu trigger shows the active character portrait
or initials fallback. GM contexts use a generic account icon because the GM is
not a character.

### Mobile

The shell stacks rather than squeezing the desktop columns:

1. Compact application header with navigation access, Hoard identity, and
   account access.
2. Campaign context strip with campaign identity and current in-world date.
3. Global PartyRail as a compact horizontally scrollable roster.
4. Routed main workspace.
5. Persistent mobile navigation.

The mobile rail has an explicit Expand roster control. Expansion reveals the
full roster or combat initiative order inline or in an accessible full-width
drawer. No player or GM functionality is removed at this breakpoint.

### Shared shell, distinct workspaces

Player and GM views use the same AppShell.

- Play is a character-focused workspace: the player’s complete playable sheet
  is primary, while campaign state is available in the header/context strip and
  PartyRail.
- GM is a command-focused workspace: campaign controls, encounter controls,
  shared resources, and approvals are primary. PartyRail stays visible and
  becomes the initiative tracker in combat.

## PC Play screen

The PC Play screen is the player’s own character profile, not a separate page
or route. It is the player’s campaign table and presents three related areas:

1. The player character
   - Full playable profile: HP and temporary HP, AC, initiative, ability scores
     and saves, skills, spell slots, inventory, equipment, effects, spells,
     features, notes, companions, and recent activity.
   - Permission-gated controls for rests, inspiration, HP, coins, inventory,
     effects, and casting.

2. The party
   - Shared XP and progress to the next level.
   - Party money and wealth.
   - A live Party Rail showing players, the GM, and—during combat—the initiative
     order.

3. The campaign
   - Current in-world date and era.
   - Campaign name and system/context.
   - Relevant campaign notices and realtime updates.

Desktop gives the player sheet the main reading area and the global campaign
roster a persistent rail. Mobile promotes immediate character state, then shows
the global rail as a compact horizontally scrollable or expandable equivalent.

### Device priority

- PC Play is mobile-first. It must be comfortable and complete on a phone, while
  using additional tablet and laptop space for a wider sheet and persistent
  supporting information.
- The GM screen is laptop-first because it supports denser campaign controls and
  administration. It must nevertheless be fully usable on a phone: no command,
  permission-gated action, form field, table value, or dialog flow may become
  unavailable at a small viewport.
- Use Bootstrap responsive breakpoints and progressive layout changes rather than
  maintaining separate mobile and desktop implementations.
- On desktop, the global Party Rail begins compact and expands into a wider
  application-shell column. On phone, it remains an always-available compact
  horizontal rail or expandable full-width section.

## Party Rail and initiative tracker

PartyRail is a live campaign roster with two explicit modes.

### Outside combat

- The GM is pinned at the top or left and shows connectivity status only.
- GMs are never player characters and never have an HP bar, character stats, or
  an initiative slot.
- Player characters follow, sorted by connectivity status and then character
  name.
- The active player’s visible label is **You**. Its accessible name still includes
  the character name and current HP.
- Player entries show an avatar or initials fallback, connectivity status,
  character name, and HP.
- A character's first active condition replaces the connectivity OverlayBadge
  on their avatar so the more urgent play state remains visible in the compact
  rail. Connectivity remains in the badge's accessible description. Further
  conditions appear only in the expanded rail, preventing badges from colliding
  in the compact horizontal and vertical layouts.
- Use only the presence states the system can report reliably: Connected and
  Offline. Do not infer Away, busy, or similar states from browser visibility.
- Connectivity comes from the acting context's campaign WebSocket. Connecting
  and disconnecting broadcasts `campaign.presence_changed` to the campaign
  group, while a heartbeat updates `CampaignContext.last_seen_at` so stale
  sockets become Offline without relying on browser visibility.
- Player characters may have a PNG, JPEG, or WebP portrait. The browser uploads
  image bytes as multipart HTTP and subsequently fetches the returned media URL;
  image bytes are never embedded in WebSocket messages. PartyRail falls back to
  initials when no portrait is available.
- `CharacterAvatar` owns portrait display and initials fallback across the
  account trigger, PartyRail, roster previews, and profile header. Character
  directory cards show a medium preview; the profile header uses the largest
  responsive presentation.

### During combat

- The GM remains pinned separately as a presence-only entry.
- A visible separator labelled **Game Master** distinguishes the GM from the
  roster.
- Combatants appear in initiative order. Do not store a PC/NPC/monster display
  enum: a linked `Character` identifies a campaign character, an optional
  Compendium creature link records creature provenance, and an entry with
  neither relationship is encounter-only.
- A character may have more than one position in the initiative order. Those
  entries have independent initiative values but share character-owned HP and
  conditions.
- At the start of combat, each player enters their own bare d20 roll from 1 to
  20 in a modal prompt that opens automatically in that player's campaign
  context. The prompt cannot be dismissed while the roll is pending. The client
  shows the resulting initiative after applying the character's Dexterity
  modifier. A natural 20 places that entry ahead of ordinary results and opens a
  second-roll prompt; a character can have at most two entries from this rule.
- Equal resulting initiatives are ordered by the higher Dexterity modifier. If
  those modifiers are also equal, every affected player can choose which tied
  entry should act first. A unanimous choice wins. If every affected player has
  voted but their choices disagree, Hoard randomly selects one tied entry and
  persists that result for stable ordering. No provisional or random choice is
  revealed while votes are still outstanding.
- The player profile keeps the exact-tie decision visible after a vote. It shows
  a live vote count for every tied entry, the number of players who have voted,
  and the final unanimous or random result once every player has voted. The
  voting player also receives an immediate confirmation Toast; campaign change
  events refresh the shared tally for every player.
- Exact-tie choices are stored on the active encounter in
  `initiative_tie_choices`. This JSON object has decimal-string
  `CampaignContext` primary keys and integer `EncounterCombatant` primary-key
  values, for example `{"12": 47, "18": 47}`. JSON requires object keys to be
  strings. A vote is accepted only when the voting context owns an entry in the
  exact tie group and the chosen combatant belongs to that same group. The
  object is temporary encounter state, is cleared whenever an initiative roll
  changes or combat ends, and disappears with the encounter when it is deleted.
- Non-unanimous results are stored separately in `initiative_tie_breaks`. Its
  JSON keys are stable comma-separated sorted combatant IDs identifying the
  exact tie group, and each value is the randomly selected combatant ID. A value
  is created only after every eligible context has cast a valid vote and those
  votes disagree. It is cleared with the vote data when rolls change or combat
  ends.
- The encounter stores the exact initiative entry whose turn is current. The GM
  can select a turn directly or move backward and forward through the order,
  including repeated positions for the same character.
- When a player's own entry is current, that player can end their turn. The
  command is rejected for every other context and advances to the next rolled
  entry, wrapping at the end of the order.
- Highlight the current entry in both the Party Rail and GM encounter controls
  with an icon and structural emphasis, not colour alone. When a player's own
  entry becomes current, attempt a short vibration and fall back to a brief tone
  where browser permissions and device support allow it.
- GM encounter controls provide quick damage, healing, and condition actions for
  each combatant. Character health changes retain the normal health ledger;
  encounter-only health remains transient encounter state.
- Each combatant entry can show a token/avatar, name, and applicable health
  information. Initiative values remain GM-only and live in the expanded combat
  controls rather than the rail presentation.
- Each combatant entry shows active status-condition icons. Icons must have an
  accessible text equivalent and expose the condition name and relevant details
  on keyboard focus as well as pointer hover.
- The GM controls whether NPC and enemy HP bars and HP numbers are visible to
  players, independently for each combatant.
- The Party Rail is the concise initiative tracker; do not create a competing
  tracker for the same information.
- PartyRail is supplemental, read-only campaign state. It never contains forms,
  questions, mutation buttons, or GM visibility/condition controls. Pending
  initiative rolls use the shell dialog; exact-tie choices and the current
  player's End turn action appear at the top of their character profile. The
  current-turn message remains sticky while the profile scrolls. GM mutations
  remain in the GM encounter desk.

### Entry visual language

- Use PrimeVue Avatar with an image where available and initials as a reliable
  fallback.
- Use OverlayBadge for connectivity or status.
- Use a compact ProgressBar for HP, accompanied by explicit text such as
  “28 / 40 HP”.
- Colour may reinforce health or presence state, but must not be the only signal.
- The rail is focusable and keyboard-operable. Entries link to an appropriate
  profile or context where permissions allow.
- Keep the visual style calmer than the reference image: dark tabletop surfaces,
  parchment-gold accents, restrained status colour, and no decorative glow-heavy
  treatment.

### Presence and status icons

- A filled status badge with a check mark means Connected; an outlined or muted
  badge means Offline. The status name must be exposed in accessible text and in
  the member’s accessible name. The Normal palette uses familiar green and grey;
  the Colourblind Friendly palette uses its blue/pink/yellow system.
- A brief reconnecting indicator is local to the current client, shown in the
  application shell or on the current user's entry while its own WebSocket is
  reconnecting. It is not a shared presence state.
- A person is Connected when they have at least one authenticated, live campaign
  WebSocket connection. Multiple browser tabs or devices do not duplicate an
  entry or cause flicker.
- Presence is operational shell state, not campaign history. Store the latest
  heartbeat on `CampaignContext.last_seen_at`; do not create a separate presence
  history or send portraits through the socket.

### Conditions

- Support the fifteen standard D&D 5e conditions: Blinded, Charmed, Deafened,
  Exhaustion, Frightened, Grappled, Incapacitated, Invisible, Paralyzed,
  Petrified, Poisoned, Prone, Restrained, Stunned, and Unconscious.
- Support Obojima's Pacify condition as a first-class condition, not an
  unstructured note or a one-off display exception. On page 165, Obojima defines
  a pacified creature as unable to attack, cast a spell that affects an enemy,
  or deal damage to another creature. Pacify is binary rather than levelled.
- Conditions on campaign characters belong to the character and remain active
  outside and across encounters, including non-combat conditions such as
  exhaustion from hunger. Encounter-only creatures keep conditions on their
  encounter entry.
- Active condition state and condition history are separate concerns. The active
  record drives the character sheet and Party Rail; every application, material
  change, and removal posts an immutable, campaign-dated condition ledger event
  containing the actor, affected target, condition, source, duration, and
  before/after values.
- Applying a condition through an initiative entry linked to a Character changes
  that Character's persistent condition state and posts the same ledger event as
  an out-of-combat application. Combat is context for the action, not a separate
  copy of the condition.
- Conditions on encounter-only combatants also produce ledger events. The event
  retains a target-name snapshot and optional encounter reference so its history
  remains intelligible if the active combatant is later removed.
- Standard conditions do not stack mechanically, but each effect imposing the
  same condition remains an independent active cause with its own source and
  duration, as required by both the 2014 and 2024 rules. The UI presents one
  deduplicated condition indicator while allowing its individual causes to be
  inspected and ended independently. The condition remains active until its
  final cause ends.
- Exhaustion is the exception: store one levelled condition per target and post
  each increase, decrease, or removal to the condition ledger.
- Players can see condition ledger events affecting their own character. The GM
  can see condition events for every character and encounter-only combatant.
- An icon is a compact visual aid, not the sole representation. The rail must
  provide condition names to screen readers and an accessible way to inspect the
  active conditions.
- Exhaustion must carry its level where applicable.

## Data and realtime requirements

- The initial campaign query includes character, party-resource, and member
  presence data needed by the shell.
- Connectivity updates through `campaign.presence_changed` realtime events. Do
  not infer presence from character existence.
- Add an application-level presence heartbeat and expiry window. Normal socket
  disconnects remove presence immediately; a missed heartbeat removes it only
  after the expiry window, preventing stale connections from appearing online
  forever without making brief network interruptions cause excessive flicker.
- Presence tracking must reference-count a person’s active campaign connections
  so multiple tabs and devices still produce one Connected state.
- Combat initiative and per-combatant HP visibility require explicit combatant
  display-policy data and realtime update events.
- Combatants require structured condition data, including condition identifier,
  optional source, duration, and condition-specific values such as exhaustion
  level.

## Accessibility baseline

- PrimeVue Toast is the standard transient feedback surface for alerts,
  confirmations, and asynchronous command outcomes. Position Toasts at the
  bottom centre on phone layouts and bottom right on larger viewports. Reserve
  Message for persistent page state, inline guidance, and validation that users
  need to revisit in context.
- Target WCAG 2.2 AA.
- Use semantic landmarks, headings, native forms, and native tables whenever
  possible.
- Maintain visible keyboard focus, accessible icon controls, 200% zoom/reflow,
  contrast, and non-colour state cues.
- Tables retain captions, scoped headers, zebra striping, and mobile handling.
- Support red–green colour-vision deficiency with a dedicated selectable
  palette. In every palette, pair colour with plain text, icons, shapes,
  patterns, position, or all of these for presence, health, destructive actions,
  and initiative state.
- Support ADHD by making hierarchy predictable, reducing competing visual
  emphasis, avoiding unnecessary animation, and allowing important state to be
  scanned quickly.
- Support dyslexia with legible type, plain labels, stable layout, comfortable
  line length and line height, and no essential meaning conveyed by dense or
  decorative text.
- Support dyscalculia with consistently formatted numeric values, explicit
  labels and units, tabular numerals in data-heavy views, clear calculation
  breakdowns, and no reliance on mental arithmetic.

## Implementation record

- 2026-09-14: began the clean replacement frontend. PrimeVue 4.5 and the Lara
  preset replace the PrimeVue 5 and licence-manager dependency. Bootstrap is
  the layout and utility foundation.
- 2026-09-14: replaced the legacy application chrome with a new AppShell. Its
  desktop grid is navigation, main content, and an in-grid narrow Party Rail;
  the rail expands without overlaying content. On smaller screens it becomes a
  compact horizontal rail above the main content and can expand into the page.
- 2026-09-14: added persistent Light/Dark/System selection and Normal/
  Colourblind Friendly palette selection. Shared presence is supplied by the
  campaign query, heartbeat command, and `campaign.presence_changed` events.
- 2026-09-14: made the player’s own character profile the canonical play
  destination. Player contexts resolve directly to
  `/c/:id/characters/:characterId`; the separate `/c/:id/play` route and
  `PlayView` were removed. The profile now includes campaign date, shared XP,
  party money, and party wealth alongside the full character sheet.
- 2026-09-14: fixed the desktop shell grid so wide main content cannot paint
  across the Party Rail column. The rail has an explicit in-grid surface and
  remains narrow but visible on desktop.
- 2026-09-14: rebuilt the GM desk hierarchy around campaign context, shared
  resources, date controls, and explicit command forms. Existing commands and
  their realtime refresh behaviour are retained, but the old dashboard and
  form presentation are not.
- 2026-09-14: rebuilt sign-in, invitation acceptance, and campaign selection
  as Bootstrap-first public pages. Their authentication and invite flows are
  unchanged; their old layout classes are not retained.
- 2026-09-14: rebuilt the campaign roster as a responsive semantic roster with
  separate player-character and GM-only NPC sections. It continues to use the
  established data query and realtime refresh mechanism.
- 2026-09-14: rebuilt the compendium as a Bootstrap-first library and source
  management workspace. Item editing, source enablement, and community-registry
  import events retain their existing WebSocket behaviour.
- 2026-09-14: rebuilt the ledger as an accessible responsive audit table with
  a caption, scoped headers, zebra rows, tabular numeric amounts, and a fresh
  reversal confirmation flow. Reversal remains a compensating command; history
  is never erased.
- 2026-09-14: rebuilt campaign management as a GM-only responsive workspace
  for members, invitations, campaign tools, and NPC lifecycle. The existing
  WebSocket commands and campaign refresh semantics remain unchanged.
- 2026-09-14: rebuilt the character builder into a responsive six-step semantic
  wizard. Draft, import, choice-loading, validation, resume, and completion
  behaviour remain intact while the old page framing and utility layout are
  removed.
- 2026-09-14: rebuilt level-up to use the same wizard language as the builder:
  visible progression, native radio fieldsets, responsive ASI controls, and an
  accessible before/after change table. The existing preview and complete
  commands remain unchanged.
- 2026-09-14: rebuilt the full character profile around Bootstrap's responsive
  structure, typography, cards, and numeric alignment. Character actions use
  labelled PrimeVue dialogs with Bootstrap-responsive form layouts and explicit
  footers while preserving the existing commands and permission checks.
- 2026-09-14: corrected all direct PrimeVue dialog bindings to the PrimeVue 4
  `visible` model and event contract. This removes a compatibility-layer-era
  interaction mismatch while preserving each dialog’s page-owned state.
- 2026-09-14: rebuilt the shared calculation display with native disclosure
  semantics and Bootstrap positioning rather than bespoke popover CSS. It
  remains a reusable explanation of derived character values.
- 2026-09-14: standardised contextual action lists on a shared PrimeVue popup
  menu with labelled icon triggers. Native disclosures remain reserved for
  expandable content such as calculation breakdowns and sheet sections.
- 2026-09-14: moved global campaign and party context out of the character
  profile. The shell header now pairs campaign name with campaign date, while
  the expanded Party Rail owns the shared XP, money, and wealth summary.
- 2026-09-14: made Party Rail resources persistent at every rail state. The
  collapsed desktop rail anchors compact XP and wealth at its foot; collapsed
  mobile uses a single-line summary below the roster; expanded rails retain the
  fully labelled values. Mobile expansion now uses vertical direction cues.
- 2026-09-14: corrected the rail footer to anchor to the desktop viewport rather
  than the full document height. Expanded mobile rails now use a vertical group
  hierarchy, an unlabelled GM/member divider avoids repeating “Party”, and the
  rail uses a distinct shell surface to separate it from page content.
- 2026-09-14: standardised displayed monetary values at exactly two decimal
  places, including compact rail wealth and item prices. Discrete denomination
  counts remain whole coin counts.
- 2026-09-14: aligned the Game Master presence entry with rail members: expanded
  views show the username with a “Game Master” role label, while compact views
  use “GM”. Expanded mobile members stretch to the rail width, and expanded
  desktop rails have additional edge spacing.
- 2026-09-14: added Django first and last names to campaign membership payloads.
  GM presence displays the first name and derives initials from first and last
  names, falling back to the username when no first name is recorded.
- 2026-09-14: rebuilt the character-profile Add Item and money-action dialogs
  with semantic headings, labelled PrimeVue 4 fields, and Bootstrap-responsive
  layouts. Their inventory and ledger commands remain unchanged.
- 2026-09-14: simplified 5e Companion import to a native, labelled `.cah` file
  input. Selecting a file immediately prepares the editable preview. Preview
  choices use PrimeVue 4 binary checkboxes and icon-backed proficiency
  SelectButtons with accessible text, while the persistent Dialog footer exposes
  Import only after preview succeeds. Imported strings, numbers, booleans,
  language lists, and all nine spell-slot levels use controls matching
  their data types rather than exposing JSON as a generic text area. Numeric
  fields use horizontal minus/plus steppers; the compact spell-slot grid uses
  vertical chevron steppers.
- 2026-09-14: restored the character builder's visible form language after the
  PrimeVue 4 rewrite. Ancestry overrides now have an explicit switch label and
  explanation; every ability has a named fieldset for its raw score, ancestry
  bonus, manual adjustment, and calculated total. Later builder steps likewise
  use visible labels, working PrimeVue option props, and horizontal numeric
  steppers instead of relying on unsupported Vuetify-style component props.
- 2026-09-14: finite Compendium fields now use PrimeVue's filterable Select
  controls. Race, class, and background lists are populated on opening, and a
  subrace Select appears only when the selected race supplies choices.
  MultiSelect is used for finite multiple-choice mode; AutoComplete remains
  reserved for fields that genuinely permit custom text.
- 2026-09-14: builder languages use the same explicit editable-list pattern as
  the 5e Companion import preview, with one labelled input per language and
  accessible add and remove controls. Blank rows are discarded when saving;
  the previous guidance about retaining `Choose 1` instructions was removed.
- 2026-09-14: skill proficiency editing in the builder and 5e Companion import
  preview now shares one icon-backed PrimeVue SelectButton component. Each
  control retains a visible skill label and accessible proficiency names.
- 2026-09-14: completed the character profile's true Options API conversion.
  Its page state now lives directly in `data`, derived values in `computed`,
  actions in `methods`, and initial loading in `mounted`; the composition-style
  ref factory was removed without changing its routes or commands.
- 2026-09-14: added a shared, keyboard-focusable condition indicator for the
  initiative rail. It maps all fifteen standard conditions and Obojima's Pacify
  to distinct MDI symbols, keeps condition names as accessible text, and exposes
  exhaustion level, duration, and source details when present.
- 2026-09-14: replaced the profile's large XP progress card with a compact level,
  current XP, and XP-remaining subheader beneath the character name. The
  near-level-up gold emphasis is controlled by the clearly named
  `NEAR_LEVEL_UP_XP_THRESHOLD` constant.
- 2026-09-14: defined encounter identity through optional Character and
  Compendium creature relationships rather than a PC/NPC/monster enum. A
  character may occupy multiple initiative positions. Character conditions are
  persistent character state and can be managed outside combat; conditions for
  encounter-only creatures remain encounter-local.
- 2026-09-14: wired active encounters and conditions into the new shell. The
  Party Rail switches to initiative order from the initial campaign payload,
  shows deduplicated condition icons, and gives GMs per-combatant condition and
  HP-visibility controls. Character profiles use the same condition editor for
  out-of-combat application, cause-by-cause editing, and removal. All mutations
  use WebSocket commands and refresh through campaign events; the ledger remains
  the immutable history rather than the source of active state.
- 2026-09-14: added the GM encounter desk. Starting combat automatically enrols
  active player characters at initiative 0; the GM can then edit initiative,
  add repeated character turns, search for Compendium creatures, add generic
  NPCs, configure player-facing HP visibility, remove initiative entries, and
  end combat. Encounter lifecycle and participant mutations use WebSocket
  commands and campaign refresh events.
- 2026-09-14: unified roster members and initiative combatants around the shared
  `PartyRailEntry` presentation component. Combat changes ordering and supplies
  extra participants and GM controls, while the avatar, condition badge, name,
  and health presentation stay consistent. Numeric initiative remains available
  only in expanded GM controls and is not displayed in the rail.
- 2026-09-14: combined character, Compendium creature, and generic NPC enrolment
  into one encounter form. Selecting an existing character hides the
  creature-specific fields; leaving it blank reveals creature search, a generic
  label, and explicit HP. Initiative remains a shared field. Every non-player
  entry exposes independent player-facing HP bar and HP-number visibility both
  when it is added and afterward in the GM encounter table; player-character HP
  remains visible.
- 2026-09-14: simplified the active encounter list into an automatically saved
  initiative order. The GM can drag entries or use accessible move-earlier and
  move-later controls; one atomic WebSocket command persists the resulting
  order. The initiative number is a compact dialog trigger for entering an
  exact value. Type and Save columns were removed, and the two NPC health
  visibility settings are icon toggle buttons with accessible pressed states.
- 2026-09-14: added explicit current-turn tracking against an exact initiative
  entry, with direct selection and wrapping previous/next GM controls. The
  current row and rail entry receive non-colour visual emphasis. Per-combatant
  shortcuts now expose damage, healing, and condition management; player-owned
  health uses ledger-backed health commands while encounter-only HP updates the
  active encounter. Player clients attempt vibration, then a short audio cue,
  when their own initiative entry becomes current.
- 2026-09-14: turn alerts now always attempt the short audio cue independently
  of vibration and also show a five-second PrimeVue Toast. The Toast sits at the
  bottom centre on phones and bottom right on larger screens. Toast is now the
  standard transient-alert pattern; persistent contextual information remains a
  Message.
- 2026-09-14: GM command confirmations, including combat damage and healing,
  now use the shell Toast host instead of inserting a full-width success Message
  into the GM desk layout.
- 2026-09-14: moved the Toast host above the authenticated/public shell split so
  every route can present transient feedback. Character-profile mutations and
  Compendium create, edit, delete, and repository-import confirmations now use
  that shared Toast host; persistent errors, warnings, progress, and explanatory
  state remain Messages.
- 2026-09-14: replaced the Party Rail's generated separator rules with explicit
  border elements. The expanded mobile initiative rail now renders a centred
  Combatants label between thin rules without the right-hand rule expanding into
  a filled block; the collapsed mobile divider remains vertical.
- 2026-09-14: softened dark-mode text from near-white to warm light grey only
  when the Melly-vision palette is selected, addressing issue 4's lower-glare
  request. Normal dark mode now uses the earlier warm grey preferred during
  visual review, while Melly-vision retains its dimmer low-glare foreground.
  Hoard, Bootstrap, and PrimeVue share each palette's foreground steps, all
  retaining AA contrast.
- 2026-09-14: restored the gold Hoard wordmark and matched it with an adaptive
  gold coin-and-H favicon. Light mode now uses a muted parchment canvas instead
  of the brighter cream background.
- 2026-09-14: unified the header, navigation, and Party Rail on one Bootstrap
  tertiary shell surface, distinct from the main content surface in Light and
  Dark modes.
- 2026-09-14: audited the rebuilt frontend against the implementation rules. All
  Vue single-file components now begin with `template`, use Options API without
  `script setup` or `setup()`, and locally import PrimeVue controls by their native
  names. Removed the remaining forwarded Vuetify-era props and events, corrected
  determinate ProgressBar values and the level-up feat Select, and restored native
  table elements for profile inventory, loadout, and effects. The final icon audit
  also corrected incomplete MDI class names on item, ledger, and campaign-management
  controls. Frontend formatting, all 26 tests, and the production build pass after
  this cleanup.
- 2026-09-14: audited the remaining presentation CSS for the Bootstrap-first rule.
  The custom rules are limited to theme tokens, shell grid behaviour, Party Rail
  geometry and health colours, and the few component layouts Bootstrap cannot
  express. Party resources now use Bootstrap's `sticky-bottom` and sizing utilities,
  and an unused rail selector was removed. The responsive shell still requires its
  custom three-column-to-stacked grid because the narrow, expandable global rail is
  application-specific chrome rather than an ordinary content grid.
- 2026-09-14: rebuilt the profile's notes, features and feats, spells, and
  companions into a shared native disclosure pattern. The sections now provide
  consistent headings and counts, explicit empty states, readable multiline
  content, spell level and preparation state, preserved casting actions, and
  semantic companion statistics. The repeated interaction lives in
  `SheetDisclosure` while the domain content remains in the existing profile
  view; layout and spacing continue to use Bootstrap utilities.
- 2026-09-14: completed the profile's remaining dense-data presentation.
  Equipment and active effects now share a clearly headed, bordered section with
  separate captioned native tables and explicit counts. Recent activity is now a
  captioned, zebra-striped ledger table with scoped headers, machine-readable
  dates, right-aligned tabular changes, and a keyboard-focusable responsive
  overflow wrapper instead of unlabeled visual rows.
- 2026-09-14: removed redundant roster request waterfalls from the GM item and
  coin command panels. The GM desk now loads the campaign, roster, and item
  catalogue once and passes the same roster snapshot to all three command forms,
  keeping sibling controls consistent with the page's initial-query model and
  realtime refresh cycle.
- 2026-09-14: simplified the character directory around one clear action per
  card: an owned character offers `Play as …`, while another visible character
  offers `View sheet`. The directory now has an explicit empty state and a
  consistently aligned GM-only NPC list. The directory, character profile, and
  GM desk all reuse the characters returned by `campaign.get` rather than
  issuing duplicate `characters.list` queries.
- 2026-09-14: completed the campaign-management page payload and layout pass.
  GM `campaign.get` responses now include invitation metadata, while player
  responses explicitly receive an empty invitation collection. Management
  therefore renders members, NPCs, and invitations from one initial query. The
  NPC list now excludes player characters, its creation fields have visible
  labels, empty invitation/NPC states are explicit, and campaign tools and NPC
  management stack in one balanced right-hand column. Successful management
  commands use the shared Toast feedback pattern.
- 2026-09-14: completed the playable profile's descriptive character data.
  Background, alignment, about text, personality traits, ideals, bonds, flaws,
  languages, and grouped equipment proficiencies are now available in two
  scan-friendly native disclosures. Empty fields are omitted inside each group
  and explicit fallback text remains, keeping optional reference material
  available without adding default-page cognitive load.
- 2026-09-14: completed a public-entry loading and failure-state pass.
  Campaign selection now distinguishes an in-progress query from a genuinely
  empty membership list, the context redirect uses Bootstrap layout utilities
  instead of legacy page classes and handles failed context queries explicitly,
  and invitation registration provides username, email, and password-manager
  autocomplete metadata.
- 2026-09-14: made character notes manageable from the playable profile. Notes
  are body-only Markdown records rather than titled documents. Owners can add or
  edit a multiline note inline, cancel an unfinished edit, and remove a note
  through an explicit confirmation. Rendered Markdown is sanitized before being
  inserted into the page. Notes are private player data: only the owning PC
  context receives or mutates them, including when the same campaign is viewed
  by its game master. All note mutations use the existing WebSocket sheet-record
  commands, refresh from shared campaign state, and report successful outcomes
  through Toasts.
- 2026-09-14: consolidated inspiration, condition, and rest commands into the
  character profile action menu. The conditions section is omitted when there
  are no active conditions, while its editor remains available from that menu.
  Inspired player names use the established accessible gold shimmer on profile,
  directory, party-roster, and initiative views, with a non-visual Inspired
  label and reduced-motion fallback.
- 2026-09-14: inspiration changes publish an authoritative, correlated
  `character.inspiration_changed` event to every connected campaign context.
  Players receive a one-step `Use inspiration` action while inspired, but only
  the GM may award inspiration. Successful use or award is confirmed with the
  standard transient Toast and the shared event refreshes every open view.
- 2026-09-14: short-rest and long-rest actions are also available from the HP
  card's action menu, reusing the same dialog and commands as the character
  action menu.
- 2026-09-14: inspiration expires 24 real-life hours after it is awarded so it
  cannot carry into a later game session. The authoritative expiry timestamp is
  distributed with character state and inspiration events; each connected
  client schedules a refresh at the next expiry so names, menus, and rails stop
  showing inspiration without requiring another user action.
- 2026-09-14: the profile money card uses the established card-flip interaction
  on phones to switch between the denomination pouch and decimal gold value.
  Coin actions remain available on either face. Tablet and desktop layouts keep
  both values visible side by side.
- 2026-09-14: installed Moment and added a shared, locally imported relative-time
  component for human-readable dates such as invitation expiry, inspiration
  expiry, recent character activity, and ledger history. Relative labels refresh
  while a page remains open, while the precise local date remains available as
  a tooltip and to assistive technology.
- 2026-09-14: the last coin display selected on the profile's mobile money card
  is stored as a browser-only preference. The pouch or decimal-value choice now
  survives reloads and follows the user between characters and campaign contexts
  in the same browser, without adding server state.
- 2026-09-14: removed the redundant visible Note field label from the note editor.
  Its add/edit heading supplies the visual context and the textarea retains an
  explicit accessible name.
- 2026-09-15: corrected profile activity dates to use the ledger's authoritative
  `occurred_at` timestamp. The relative-time component now also reports a missing
  timestamp as unavailable instead of allowing Moment to interpret it as now. A
  WebSocket regression test covers the character-history path used by inspiration,
  ensuring listed activity retains its immutable timestamp as well as command
  responses.
- 2026-09-15: adopted summary-card rotation as the standard presentation for
  derived statistics. HP, armor class, initiative, and proficiency now show only
  their play-facing values on the front and reveal their full calculation on a
  reduced-motion-safe reverse face, matching the established ability-card pattern.

## Open questions

- Decide whether later rules automation should calculate the differing 2014 and
  2024 Exhaustion effects or only track the authoritative current level.
