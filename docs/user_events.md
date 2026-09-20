# User events (projection contract)

Tessera product services (Linden, Custos, Sendly, Orcha, Eventa, Modela, ...) keep a
local `users` row with the **same Identies UUID** so they can foreign-key records
(`created_by_id`, members, actors) without calling Identies on every read. That row
is a **projection**: Identies is the only identity write path, and services keep
their copy up to date by consuming the events below.

## Events

| Event type | Published when |
|---|---|
| `user.created` | A user is onboarded (Auth0 login) or a service account is created |
| `user.updated` | A user's profile changes (`PUT /me`) or a service account is updated |
| `user.deleted` | A user is removed (currently: service-account deletion) |

The event type is namespaced by `tessera_sdk` `event_type()`, so the NATS subject and
`event_type` end in `user.created` / `user.updated` / `user.deleted`. Subject:
`/users/{id}`. Labels/tags: `user_id`.

Service accounts are users too: creating, updating or deleting one publishes the same
`user.*` events (with `service_account: true`). There are no separate `service_account.*`
events.

## Payload

`event_data["user"]` is a complete projection body:

| Field | Notes |
|---|---|
| `id` | Identies UUID. **Upsert key.** |
| `email`, `first_name`, `last_name`, `preferred_name` | |
| `avatar_url`, `avatar_asset_id` | `avatar_url` is the stored value, not a signed URL |
| `external_id`, `provider` | |
| `verified`, `verified_at`, `confirmed_at` | |
| `theme_preference` | |
| `service_account` | Computed from `kind`: `true` for `agent` and `service_account`. Prefer `kind` |
| `kind` | `human`, `agent` or `service_account`. Consumers must treat a missing `kind` as `human` |
| `created_at`, `updated_at` | |

`user.deleted` still carries the full body, including `id`, after the row is gone.

## Consumer rules

- **Upsert by `id`.** Handle `user.created`, `user.updated` and `user.deleted` (delete or
  soft-delete the local row; keep it as a tombstone if other rows reference it).
- **Be idempotent and order-tolerant.** Delivery is at-least-once in intent, but see
  Durability. Use `updated_at` to ignore an older event that arrives after a newer one.
- **Ignore unknown fields, tolerate missing ones.** A missing `kind` means `human`. New fields are added additively.
  Removing or renaming a key under `event_data.user` requires a version bump.

## Durability

Publishing is best-effort: NATS failures are logged and swallowed, so a projection can
miss an event. Consumers must tolerate that (for example, refresh from Identies when a
row looks stale). There is no outbox in Identies today.

## Not covered yet

- There is no human-user delete path in Identies, so `user.deleted` is only emitted for
  service accounts. When human deletion exists it must publish `user.deleted`.
