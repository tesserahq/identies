# Data Lifecycle

What happens to data over a principal's life, and what deletion means.

## Users are soft-deleted

Deleting a user does not remove the row. It sets `deleted_at`, and the row stays as a
**tombstone** so records in other services that reference the user's id still resolve.

While a user is deleted:

- Every lookup and list in Identies **excludes** them. `get_user(..., include_deleted=True)` is the only way to see the tombstone.
- Their **API keys and OAuth clients are revoked** when they are deleted, and validation also rejects a deleted user's keys and clients even if they were somehow not revoked. `POST /oauth/token` returns `401`.
- Their `email` and `external_id` can be reused by a new user: uniqueness applies only to **active** users (partial unique indexes `uq_users_email_active` and `uq_users_external_id`).
- A `user.deleted` event is published ([Events](events.md)).

Deleting is available for service accounts (`DELETE /service-accounts/{id}`) and agents
(`DELETE /agents/{id}`). There is **no delete for humans** in Identies yet.

!!! note "Only users are soft-deleted"
    Applications, external accounts, access rules, API keys and clients are removed from the
    database when deleted. Access rules, applications and clients already have a `deleted_at`
    column, but their delete does not use it yet (tracked in
    [#95](https://github.com/tesserahq/identies/issues/95)).

## Agent lifecycle

```
                claim code       claim          rotate
  POST /agents ───────────► unclaimed ───► active ◄────────┐
                              │  ▲           │  │           │
                    reissue   │  │           │  └─ expires ─► expired ─ rotate ─┐
                    code ─────┘  │           │                                   │
                                 │      revoke│                                  │
                                 │           ▼                                   │
                                 │        revoked ── rotate ─────────────────────┘
                                 │
         DELETE /agents/{id} from any state ──► deleted (tombstone)
```

| State | Meaning | How it is entered |
|---|---|---|
| `unclaimed` | No credentials yet. A claim code may be open | `POST /agents`; a lapsed or revoked code stays here |
| `active` | The client can mint tokens | A successful claim; `rotate` |
| `expired` | The client secret ran out | 30 days after the last claim or rotation (`AGENT_CLIENT_SECRET_TTL_DAYS`) |
| `revoked` | Cut off | `revoke`. **`rotate` restores it** — there is no separate pause state |
| deleted | Soft-deleted; not visible | `DELETE /agents/{id}` |

Claim rows (`agent_claims`) are kept after use for auditing and are not purged automatically.
Cleaning up agents that were never claimed is done by the calling product, not by Identies.

## Credential lifetimes

| Credential | Ends when |
|---|---|
| Identies access token | 15 minutes after it was minted, whatever else happens |
| Client secret | It expires (`expires_at`), is rotated, is revoked, or its owner is deleted |
| API key | It expires, is revoked, is deleted, or its user is deleted |
| Claim code | 15 minutes, first successful use, a newer code, five wrong secrets, or the agent is revoked/deleted |

## Retention

Identies does not currently purge anything on a schedule. Tombstones, claim rows and rows for
hard-deleted resources' history (events) are retained indefinitely; if a retention policy is
introduced it must keep tombstones for as long as any service still references the user id.

## Migrations that shaped this

| Migration | Effect | Rollback caveat |
|---|---|---|
| `add_kind_to_users` | Required `kind`, backfilled from the old flag | None |
| `add_soft_delete_to_users` | `deleted_at`; partial unique indexes for `email` and `external_id` | Downgrade **fails** if a soft-deleted and an active user share an email or external id; resolve those first |
| `add_agent_claims_table` | `agent_claims` | Drops the table |
| `add_expires_at_to_clients` | Optional client expiry | Drops the column |
| `add_last_used_at_to_clients` | Client `last_used_at` | Drops the column |
