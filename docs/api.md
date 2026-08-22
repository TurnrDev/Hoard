# Campaign JSON API

The JSON API is served by Django Ninja at `/api/`; interactive OpenAPI docs are
available at `/api/docs`. It uses Django session cookies and CSRF protection.
Obtain a token with `GET /api/auth/csrf/`, sign in with `POST /api/auth/session/`,
inspect the current user with `GET /api/auth/session/`, and sign out with
`DELETE /api/auth/session/`.

All campaign endpoints live below `/api/campaigns/<campaign_id>/`. Ninja
returns `401` for missing sessions, `403` for unauthorized members, `404` for
missing resources, and `422` for invalid request schemas or domain input.

## Resources

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /api/campaigns/` | authenticated | Active campaign memberships. |
| `GET /` | member | Campaign state, active-PC balances, and party total. |
| `GET`/`POST /members/` | member / GM | List members or add a user by username. |
| `PATCH`/`DELETE /members/<id>/` | GM | Change GM role or deactivate membership and archive its characters. |
| `GET`/`POST /characters/` | member | Visible characters and self-owned character creation. |
| `GET /characters/me/` | member | All of the caller's characters, including inactive or archived records. |
| `GET`/`PATCH`/`DELETE /characters/<id>/` | owner / GM | Read, update, or archive a character. |
| `POST /inventory-transactions/` | GM/member | Move one item between characters or the system. |
| `POST /money-transfers/` | GM/member | Move positive coin amounts between characters or the system. |
| `POST /money-exchanges/` | GM/member | Exchange equal copper value for one character. |
| `POST /shared-xp-awards/` | GM | Create a shared-XP award. |
| `GET /transactions/` | member | Paginated, role-scoped ledger history. |
| `GET`/`DELETE /transactions/<ledger>/<id>/` | member / initiator or GM | Read a transaction or create its compensating reversal. |

Inventory transaction payloads use `from_character_id` and `to_character_id`;
`null` represents the campaign system account. Money transfers use the same
parties plus a positive denomination map. A member may only send money from
their own character, but may return it to the system; members can exchange
only their own coins. GMs may post all supported ledger changes.

Transactions are immutable. DELETE is available only for the latest record in
the matching campaign ledger and creates a final compensating transaction. It
returns that reversal with `200`; the original remains in collection history
but its detail URL returns `410 Gone`.

## Compendium WebSocket API

Compendium operations use the campaign WebSocket at
`/ws/campaigns/<campaign_id>/`, rather than HTTP endpoints. Each request has a
unique `request_id`; the server replies with `response` or `response.error`
carrying the same ID.

| Message type | Access | Purpose |
| --- | --- | --- |
| `compendium.items.list` | member | List enabled equipment entries in bounded pages (`offset`, `limit`). |
| `compendium.items.create` | member | Create a campaign-local item. |
| `compendium.items.update`/`delete` | GM | Change or delete a local item. |
| `compendium.search` | member | Search enabled entries by kind and name. |
| `compendium.sources.list` | member | List sources available to the campaign. |
| `compendium.sources.enable`/`disable` | GM | Change the campaign's enabled sources. |
| `compendium.repositories.list` | member | List compatible community-registry repositories. |
| `compendium.repositories.import` | GM | Queue installation of a registered repository. |

## Money visibility

Campaign state includes `party_money`, a denomination map and gold-equivalent
value summed across active player characters only. Each visible active PC also
includes their own `money` balance. NPCs, inactive/archived PCs, and campaign
system accounts are excluded from the party total.

## Client controls

The campaign screen is read-focused: it shows the party total, every visible
character balance, inventory, and immutable ledger history. It has no generic
transaction/action picker. GM controls provide separate Give item, Take item,
Give/Take coins, and shared-XP forms. Character actions provide separate Move
item, Send money, and Exchange money forms for a member's own active
characters; each form calls its matching concrete resource endpoint.

## Item metadata

Item `metadata` is optional and has this shape: `{ "category", "source_book",
"item_type", "cost_amount", "cost_currency", "weight_amount", "weight_unit",
"rarity", "is_magic", "requires_attunement" }`. Costs use `cp`, `sp`, `ep`,
`gp`, or `pp`; amount and currency must be supplied together, as must weight
amount and unit.
