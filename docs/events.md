# Events

Identies publishes an event whenever something it owns changes. Other services consume them to
keep local copies current (see [User Events](user_events.md) for the user projection contract)
or to audit and react.

## Delivery

- Events are CloudEvents published on NATS by the command that made the change. The NATS subject is the full event type.
- **Nothing is published unless `NATS_ENABLED=true`** (a shared SDK setting, off by default; `NATS_URL` says where). When it is off the event is skipped and only logged.
- The event type is `<prefix>.<name>`, where the prefix comes from the shared SDK setting
  `EVENT_TYPE_PREFIX`. The names below are what follows the prefix.
- Publishing is **best-effort**: a failure is logged and swallowed, and there is no outbox. A
  consumer can miss an event, so it must tolerate that (for example by refreshing from Identies
  when a row looks stale).
- **No event ever contains a secret**: client secrets, API key secrets and claim codes are never published.
- Every event carries `subject`, `user_id`, `labels` and `tags`, listed per event below.

## Catalog

| Event | Published when | `event_data` | Subject |
|---|---|---|---|
| `user.created` | A human is onboarded; a service account or an [agent](agents.md) is created | `user` (full projection body) | `/users/{id}` |
| `user.updated` | A profile changes (`PUT /me`) or a service account is updated | `user` | `/users/{id}` |
| `user.deleted` | A service account or an agent is deleted | `user` (still includes `id`) | `/users/{id}` |
| `user.offboarding_scheduled` | An admin schedules a human for offboarding (nothing is deleted yet) | `user`, `offboarding_scheduled_at`, `offboarding_scheduled_by` | `/users/{id}` |
| `api_key.created` | An API key is created | `api_key`, `user` | `/api-keys/{id}` |
| `api_key.updated` | An API key is updated or revoked | `api_key`, `user` | `/api-keys/{id}` |
| `api_key.deleted` | An API key is deleted | `api_key`, `user` | `/api-keys/{id}` |
| `client.created` | An OAuth client is created, including when an agent is claimed | `client`, `user` | `/clients/{id}` |
| `client.rotated` | An agent's client secret is rotated | `client`, `user` | `/clients/{id}` |
| `client.revoked` | A client is revoked, including when an agent is revoked | `client`, `user` | `/clients/{id}` |
| `client.deleted` | A client is deleted | `client`, `user` | `/clients/{id}` |
| `access_rule.created` | An invite-only access rule is created | `access_rule`, `user` | `/access-rules/{id}` |
| `access_rule.updated` | An access rule is updated | `access_rule`, `user` | `/access-rules/{id}` |
| `access_rule.deleted` | An access rule is deleted | `access_rule`, `user` | `/access-rules/{id}` |
| `link_token.created` | A link token for an external account is created | `platform`, `external_user_id`, `expires_at`, `data` | `/link-tokens/{platform}/{external_user_id}` |
| `external_account.linked` | A user links an external account | `external_account`, `user` | `/external-accounts/{id}` |
| `external_account.deleted` | An external account is unlinked | `external_account`, `user` | `/external-accounts/{id}` |

In events that have a `user`, that user is **the actor** for most events (who made the change), and
for `user.*` events it is the subject of the change.

## Agent operations

| Operation | Events |
|---|---|
| Create an agent | `user.created` (`kind: agent`) |
| Claim | `client.created` |
| Rotate credentials | `client.rotated` |
| Revoke | `client.revoked`, one per client that was active |
| Delete | `user.deleted` |

## Compatibility rules

- Adding fields to an event is not a breaking change. Consumers must ignore fields they do not know.
- Removing or renaming a key under `event_data`, or changing an event's meaning, needs a version bump and a note in this page.
- The `service_account.*` events no longer exist; service accounts publish the `user.*` events.
