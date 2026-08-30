# WebSocket migration roadmap

This roadmap completes Hoard's REST-to-WebSocket migration in small, independently reviewable domain slices. It is deliberately additive: establish WebSocket parity, move callers, then remove the corresponding REST implementation. Do not attempt a repository-wide rewrite.

## Current state and target

Campaign features are already reachable through the context, user, and invitation WebSocket endpoints. `hoard/campaigns/api.py` still contains the former REST-oriented handlers and provides payload formatting and mutation helpers used by the consumers.

The migration replaces those handler dependencies with a small, conventional Python domain layer:

* cohesive service classes for commands;
* Pydantic models as the explicit contracts for query results, command payloads, and domain events;
* thin WebSocket consumers responsible only for connection handling, envelopes, authorization context, dispatch, and response/event delivery.

The final HTTP surface is intentionally narrow:

* CSRF and session endpoints remain HTTP.
* Raw `.cah` upload bytes remain HTTP multipart transfer.
* Application-domain reads, mutations, command outcomes, and live updates use WebSocket.

## Target protocol

Hoard uses three primary application interaction types:

* **Queries** read current application state.
* **Commands** request mutations.
* **Events** notify connected clients about mutations that have occurred.

Queries and commands are initiated by clients. Events are initiated by the server.

### Request envelope

Every client request uses an envelope containing a request identifier:

```json
{
  "type": "domain.action",
  "request_id": "unique-client-id",
  "...": "payload"
}
```

`request_id` must be a freshly generated UUIDv7 (RFC 9562) for every query and
command. The server validates the format and echoes the identifier unchanged in
each correlated result, acknowledgement, error, and originating event.

The exact `type` identifies whether the operation is a query or command through its documented protocol definition; transport code should not infer behaviour from HTTP-style semantics.

### Queries

Queries return current state without modifying it.

Examples include:

* `campaign.page`
* `character.page`
* `character.list`
* `ledger.list`
* `inventory.list`
* `compendium.search`

A query receives a correlated `query.result`:

```json
{
  "type": "query.result",
  "request_id": "abc123",
  "data": {}
}
```

Page entry points should normally expose a page-oriented query returning the complete render model needed for the initial page load.

For example, opening a character sheet should not require independent requests for character details, wallet, inventory, features, and other small fragments if those values are always required together.

This is a normal current-state query, not a persistent or versioned snapshot protocol.

Search results, transaction histories, compendium collections, and other potentially large collections remain explicit queries with filters, search terms, and pagination bounds. Avoid unnecessary request waterfalls while keeping payload sizes reasonable.

Query failures return a correlated `query.error` with a stable `code`, human-readable `detail`, and `field_errors` where applicable.

### Commands

Mutations are commands.

Examples include:

* `character.create`
* `character.update_health`
* `inventory.add`
* `inventory.transfer`
* `money.give`
* `xp.award`
* `ledger.reverse`

A command asks the authoritative server to perform an action. The frontend must not treat sending the command itself as proof that the mutation succeeded.

Successful commands receive a correlated acknowledgement:

```json
{
  "type": "command.ack",
  "request_id": "abc123"
}
```

The acknowledgement confirms that the command succeeded or was accepted according to the documented semantics of that command. It does not need to contain the resulting domain state.

Command validation or execution failures return a correlated `command.error`:

```json
{
  "type": "command.error",
  "request_id": "abc123",
  "code": "insufficient_funds",
  "detail": "The character does not have enough gold.",
  "field_errors": {}
}
```

Commands that genuinely start asynchronous work, such as repository imports, may acknowledge acceptance first and later report progress or failure through correlated events.

Ordinary synchronous mutations should not introduce an artificial asynchronous lifecycle.

### Events

Successful mutations publish domain events to relevant connected clients.

Examples include:

* `character.health_changed`
* `character.archived`
* `inventory.item_added`
* `inventory.item_removed`
* `money.balance_changed`
* `xp.changed`
* `ledger.entry_created`
* `member.joined`

Events describe domain changes rather than generic CRUD implementation details where a meaningful domain name exists.

Where practical, an event should contain enough authoritative current state for clients to update their UI directly.

For example:

```json
{
  "type": "money.balance_changed",
  "character_id": 17,
  "balance": {
    "cp": 12,
    "sp": 4,
    "ep": 0,
    "gp": 18,
    "pp": 0
  },
  "request_id": "abc123"
}
```

Prefer authoritative resulting values or useful updated fragments over requiring clients to reconstruct current state from a sequence of deltas.

The originating `request_id` should be included when an event was caused by a client command. This allows the originating client to correlate the event with pending UI state while still processing the same authoritative event as every other subscribed client.

Events do **not** require entity versions, campaign versions, sequence numbers, event replay, or gap detection.

### Initial page load

Initial page population happens through queries.

A page should:

1. establish or reuse its WebSocket connection;
2. issue the page query or other necessary bounded queries;
3. render the returned current state;
4. listen for relevant domain events while the page remains active.

For example:

```text
Client                          Server

  | ---- character.page ------> |
  | <---- query.result -------- |
  |                             |
  | <--- inventory.item_added - |
  | <--- money.balance_changed -|
  | <--- character.health_changed
```

There is no separate snapshot lifecycle.

### Reconnection

WebSocket delivery is only expected while the client is connected.

After reconnecting, the frontend re-runs the queries required by the currently active page and replaces its local page state with those current query results.

Hoard does not attempt to replay every event missed during a disconnect.

This deliberately avoids:

* per-entity versions;
* campaign-wide versions;
* event sequence tracking;
* version-gap detection;
* replay cursors;
* event-log reconstruction;
* snapshot recovery protocols.

If these guarantees become necessary in future, they can be added for the domains that need them rather than imposed on the whole application now.

### Subscriptions and event scope

Clients should only receive events relevant to the contexts they are authorised to observe.

Campaign membership, acting context, character ownership, GM role, and other existing authorization rules continue to determine both:

* which queries and commands a connection may issue;
* which events that connection may receive.

Consumers should use explicit domain/event subscriptions or server-side campaign/context association as appropriate. Do not broadcast all application events to every WebSocket connection.

### Payload size

Query and event payloads must remain within the configured WebSocket message-size limits.

Large collections require explicit pagination, filtering, or narrower queries.

Page-oriented queries should group data that naturally belongs to one render operation, but should not become unbounded dumps of every object associated with a campaign.

## Delivery slices

### 1. Foundation and compatibility seam

* Document the request envelope, query/result lifecycle, command acknowledgement/error lifecycle, event naming, reconnect behaviour, authorization, subscription rules, and payload-size limits.
* Move shared mutation logic into cohesive, class-based domain services so consumers no longer invoke HTTP handler functions.
* Define query results, command payloads, and domain events with Pydantic models; use `model_dump(mode="json")` at transport boundaries.
* Give each class a named domain responsibility; do not create generic catch-all services or transport-aware business logic.
* Add frontend request correlation for queries and commands.
* Add frontend command pending/error handling.
* Add domain-event subscription and dispatch infrastructure.
* Add straightforward page re-query behaviour after WebSocket reconnection.
* Keep legacy REST handlers as temporary compatibility callers of the new domain layer where necessary.

Do not add application-wide snapshot, versioning, replay, or event-gap infrastructure.

### 2. Session, contexts, and invitations

* Add WebSocket queries and commands for acting contexts, campaign selection, invitation inspection, acceptance, registration, and member lifecycle.
* Publish targeted context, invitation, and membership events where live updates are useful.
* Keep session and CSRF HTTP endpoints as documented transport exceptions.
* Remove corresponding REST context and invitation access only after WebSocket parity and tests are established.

### 3. Campaign shell and administration

* Add a campaign/GM page query returning the current render model required for the campaign shell.
* Include campaign overview, calendar, level approval, members, and invitation information where those values are required together by the page.
* Keep independently paginated or potentially large collections as separate queries.
* Publish targeted calendar, level, member, and invitation events.
* Convert those views to an initial page query plus live event updates rather than independently loading many small fragments.
* On reconnect, rerun the relevant page queries.

### 4. Characters and character sheet

* Migrate character directory and profile/sheet queries.
* Migrate creation, archival, health, notes, features, spells, effects, loadouts, companions, resting, casting, and inspiration commands.
* Publish character-scoped events sufficient for open directory and character-sheet consumers to update their current UI state.
* Prefer events containing authoritative resulting values where useful, such as current HP after a health change.
* Preserve ownership, GM authorization, and immutable-history behaviour.

### 5. Builder, levelling, and character import

* Migrate builder definitions and drafts.
* Migrate builder save/complete commands.
* Migrate level-up definition, preview, and completion.
* Migrate import preview, commit, and cancel.
* Retain multipart `.cah` upload only for raw byte transfer.
* Keep import orchestration and application-domain results on WebSocket.
* Model genuinely asynchronous import progress with domain events.
* Use correlated `command.error` events only where a command was accepted for asynchronous processing and later failed; synchronous failures should be returned directly as `command.error`.

### 6. Ledger and inventory

* Migrate transaction history and inventory queries.
* Migrate inventory transactions, money transfers/exchanges, shared XP, and reversals as commands.
* Publish ledger-entry, inventory, XP, and balance events.
* Prefer balance events containing authoritative current balances rather than only arithmetic deltas.
* Keep history paged.
* New events may be inserted into a currently displayed first page where appropriate.
* If an event makes a loaded paginated range ambiguous or stale, mark that collection stale and rerun its query rather than introducing version tracking.

### 7. Compendium

* Migrate item catalogue CRUD, search, source enablement, repository listing/import, and repository-import progress.
* Keep searches and repository listings explicitly paginated and filtered.
* Preserve current WebSocket response-size constraints.
* Bring repository import onto the standard command acknowledgement, progress event, and command-error model.
* Publish catalogue events where other connected clients need live updates.

### 8. Retirement and hardening

* Remove migrated REST routes, schemas, and HTTP-handler dependencies, retaining only the approved HTTP exceptions.
* Update `docs/api.md` with the finished query/command/event protocol and link this roadmap as migration history.
* Add observability for query failures, command acknowledgements, command failures, event delivery, reconnect re-query, and oversized-payload rejection.
* Confirm there is no unnecessary snapshot, version, replay, or event-gap machinery remaining from the migration.

## Completion criteria for every slice

* Consumer tests cover authorization, query result shape, command acknowledgement, command validation/error handling, successful event fan-out, and multi-client updates.
* Query tests confirm page-oriented queries provide the data required to render their corresponding page without unnecessary waterfalls.
* Frontend tests cover first-load queries, pending commands, displayed command errors, authoritative event updates, and reconnect re-query.
* Frontend event handling must work the same for the client that originated a command and other subscribed clients; do not maintain separate mutation paths for the originating client.
* Paginated views test their documented behaviour when incoming events affect the currently loaded range.
* Before removing a REST slice, confirm WebSocket parity and that no frontend call site or public route depends on it.
* Run the Python and frontend test suites for each slice.
* When page loading or live-update UI changes, run the normal frontend accessibility checks too.

## Design constraints

Keep the protocol deliberately simple.

Hoard's WebSocket model is:

```text
query   -> query.result
command -> command.ack / command.error
change  -> domain event
```

Queries establish current state.

Commands modify authoritative server state.

Events keep connected clients up to date.

Reconnects cause fresh queries.

Do not introduce versioning, replay, event sourcing, distributed-state convergence, or snapshot infrastructure unless a concrete future requirement demonstrates that Hoard needs it.
