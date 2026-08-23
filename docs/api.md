# Session and WebSocket API

Hoard uses the Django session for both HTTP and WebSocket authentication. HTTP is
limited to CSRF/session operations and raw `.cah` byte transfer:

- `GET /api/auth/csrf/`
- `GET`, `POST`, and `DELETE /api/auth/session/`
- `POST /api/uploads/character-imports/<upload_id>/`

Campaign domain data is not exposed through HTTP REST routes.

## Sockets

- `/ws/user/` lists the signed-in user's active acting contexts.
- `/ws/contexts/<context_id>/` resolves that exact GM or PC context and joins its
  campaign broadcast group.
- `/ws/invites/<token>/` inspects and claims a single invitation. It supports
  anonymous inspection and registration.

Requests contain a `type`, a unique `request_id`, and command fields. Replies use
`response` or `response.error` and echo `request_id`. Errors include a stable
`code`, human-readable `detail`, and `field_errors` where validation identified
specific fields. Campaign sockets reconnect and clients authoritatively reload
after `campaign.changed` broadcasts.

The context socket exposes campaign state/calendar, members, invitations, group
levels, characters and builder drafts, HP history, `.cah` imports, sheet records,
inventory, money, XP, history, and Compendium operations. Commands follow the
names visible in `ContextConsumer`, for example `campaign.get`,
`characters.builder.save`, `characters.health.post`,
`inventory.transactions.create`, and `compendium.search`.

The invite socket supports `invite.inspect`, `invite.accept`, and
`invite.register_and_accept`. The user socket supports `user.contexts.list`.

## `.cah` transfer

1. Send `characters.imports.cah.begin` with the target character.
2. Upload one `.cah` file to the returned same-origin URL using multipart,
   session authentication, and CSRF. The endpoint returns only `204`.
3. Send `characters.imports.cah.preview` with the upload ID.
4. Review calculations, warnings, and inventory mappings.
5. Send `characters.imports.cah.commit` with the preview token, or
   `characters.imports.cah.cancel`.

Upload IDs are single-use, limited to 5 MiB, target-bound, and expire after 15
minutes. Preview and commit domain data travels only over WebSocket.

## Immutable history

Ledger and audit responses include `occurred_at`, `campaign_date`, and `actor`.
The real timestamp is UTC-backed and the campaign date is the snapshot captured
when the event posted. Unknown legacy snapshots are `null` and display as
`Campaign date unavailable`. Campaign dates are formatted like `PD 81, 21st`.
