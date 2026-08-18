# Campaign JSON API

The API uses Django session authentication and normal CSRF protection. The
frontend obtains a token from `GET /api/auth/csrf/`, then posts credentials to
`POST /api/auth/login/`; `POST /api/auth/logout/` ends that session and
`GET /api/auth/session/` returns the signed-in user. Every
endpoint is scoped to a campaign membership at `/api/campaigns/<campaign_id>/`.
Campaign game masters may post ledger actions; any campaign member may create a
shared custom item.

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /` | member | Campaign state. GMs receive every character; players receive their own characters. |
| `GET /api/campaigns/` | authenticated | Campaign memberships for the campaign picker. |
| `GET /items/` | member | Campaign-local items plus global imported items enabled by the campaign's `item_sources` setting. |
| `POST /items/` | member | Create `{ "name", "description", "metadata" }` custom campaign equipment. |
| `POST /items/<item_id>/copy/` | GM | Make an editable campaign-local copy of a global item, optionally overriding `metadata`. |
| `POST /actions/<action>/` | GM | Post a domain action. |
| `POST /transactions/<ledger>/<id>/reverse/` | GM | Reverse an inventory, money, or experience transaction. |
| `GET /transactions/` | member | Paginated ledger history; GMs receive all history and players receive entries involving their characters. |

Available actions and payloads:

- `grant-loot`: `{ "recipient_id", "item_id", "quantity", "description" }`
- `take-loot`: `{ "source_id", "item_id", "quantity", "description" }`
- `transfer-item`: `{ "source_id", "recipient_id", "item_id", "quantity", "description" }`
- `grant-coins` and `spend-coins`: `{ "character_id", "coins": {"gp": 5}, "description" }`
- `exchange-coins`: `{ "character_id", "given": {"gp": 1}, "received": {"sp": 10}, "description" }`
- `preview-shared-xp` and `award-shared-xp`: `{ "amount", "description" }`

Coin maps accept `cp`, `sp`, `ep`, `gp`, and `pp`; values must be positive
integers. Exchanges must have equal copper value. Posted actions return their
transaction metadata, while XP actions return `{ "per_character", "dry_run" }`.
Invalid input produces DRF’s structured `400` response; missing campaign
membership is `404`, and a non-GM mutation is `403`.

Item `metadata` is optional and has the following shape. Null or omitted facts
mean unknown: `{ "category", "source_book", "item_type", "cost_amount",
"cost_currency", "weight_amount", "weight_unit", "rarity", "is_magic",
"requires_attunement" }`. Costs use `cp`, `sp`, `ep`, `gp`, or `pp`; an amount
and currency must be provided together, as must a weight amount and unit.

## Item source settings

Each campaign stores `item_sources` as a list of enabled imported catalogue
systems, currently `5e` and `5e2024`. Configure it from the campaign’s Django
admin page with the source checkboxes. The item API and item pickers only show
global items from enabled sources; campaign custom items are always available.
Disabling a source never removes items already held by a character, and those
items may still be returned to the system account.
