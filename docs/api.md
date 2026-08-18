# Campaign JSON API

The API uses Django session authentication and normal CSRF protection. Every
endpoint is scoped to a campaign membership at `/api/campaigns/<campaign_id>/`.
Campaign game masters may post ledger actions; any campaign member may create a
shared custom item.

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /` | member | Campaign state. GMs receive every character; players receive their own characters. |
| `GET /items/` | member | Global imported and campaign-local item catalogue. |
| `POST /items/` | member | Create `{ "name", "description" }` custom campaign item. |
| `POST /items/<item_id>/copy/` | GM | Make an editable campaign-local copy of a global item. |
| `POST /actions/<action>/` | GM | Post a domain action. |
| `POST /transactions/<ledger>/<id>/reverse/` | GM | Reverse an inventory, money, or experience transaction. |

Available actions and payloads:

- `grant-loot`: `{ "recipient_id", "item_id", "quantity", "description" }`
- `transfer-item`: `{ "source_id", "recipient_id", "item_id", "quantity", "description" }`
- `grant-coins` and `spend-coins`: `{ "character_id", "coins": {"gp": 5}, "description" }`
- `exchange-coins`: `{ "character_id", "given": {"gp": 1}, "received": {"sp": 10}, "description" }`
- `preview-shared-xp` and `award-shared-xp`: `{ "amount", "description" }`

Coin maps accept `cp`, `sp`, `ep`, `gp`, and `pp`; values must be positive
integers. Exchanges must have equal copper value. Posted actions return their
transaction metadata, while XP actions return `{ "per_character", "dry_run" }`.
Invalid input produces DRF’s structured `400` response; missing campaign
membership is `404`, and a non-GM mutation is `403`.
