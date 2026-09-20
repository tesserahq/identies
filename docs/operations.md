# Operations

Deploying, configuring and running Identies, and what to do when something goes wrong.

## Deploying

1. **Run migrations first** (or together with the rollout): `alembic upgrade head`.
2. Roll out the new version.
3. Check `GET /livez` and `GET /readyz`. Note that `/readyz` does not verify the database, so also confirm a real request (for example an authenticated `GET /me`) succeeds after a migration.

### Migration notes

Every migration in this series changes `users` or adds a table. Read the row for the ones you are
about to apply.

| Migration | Rollout note |
|---|---|
| `add_kind_to_users` | Adds a `NOT NULL` `kind`, backfilled from the old flag, in one transaction that briefly locks `users`. **Pods still on the old code create users without `kind`**, which now fails, so a first-time login on an old pod can fail during the rollout. Migrate and roll out together, off-peak if `users` is large |
| `add_soft_delete_to_users` | Adds `deleted_at` and swaps the unique email and external-id constraints for partial indexes, in one transaction that briefly locks `users`. Nothing is soft-deleted before it ships, so old pods are safe |
| `add_agent_claims_table` | New table only |
| `add_expires_at_to_clients` | Nullable column; existing clients never expire |
| `add_last_used_at_to_clients` | Nullable column; each successful token mint now writes one row update |

Downgrades work, with one caveat: after `add_soft_delete_to_users`, downgrading **fails** if a
soft-deleted and an active user share an email or external id. Resolve those rows first.

There are no automated migration tests in this repository. When you change a migration, run
upgrade, downgrade and upgrade again against a database with realistic data.

### Signing keys

Tokens are signed with the RSA key in `TOKEN_EXCHANGE_PRIVATE_KEY_PEM` and published at
`/.well-known/jwks.json`. The key set contains **exactly one key** and is built once per process.
That means:

- There is **no overlap period** for rotating the key. Changing it invalidates every Identies-issued token still in flight (at most 15 minutes for client tokens, 10 for delegated tokens by default).
- Consumers must pick up the new key. PyJWT's `PyJWKClient` refetches the key set when it sees an unknown `kid`; other clients may cache longer.
- Plan a key change like a short, planned blip: change the key pair, restart, expect brief `401`s.

Generate a pair with any standard tool (for example `openssl genrsa` and `openssl rsa -pubout`),
keep the private key in your secret store, and set both PEMs and, optionally, a stable
`TOKEN_EXCHANGE_KEY_ID`.

## Letting a service call Identies

### A service that will call the service-only endpoints (`/agents`, `/internal/users`, `/oauth/token-exchange`)

1. Create a service account: `POST /service-accounts`.
2. Create a client for it: `POST /service-accounts/{id}/clients`. Save the secret; it is shown once.
3. The service exchanges the client for a token at `/oauth/token` and calls the endpoints. Identies-issued service-account tokens are trusted without an allowlist entry.
4. If the service instead uses an **OIDC machine-to-machine token**, add its client id to `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`.

### A service that must accept Identies-issued tokens (agents, service accounts)

Add Identies as an auth provider in the consuming service (the shared SDK reads
`AUTH_PROVIDERS_JSON`, a list with one entry per provider):

```json
[
  {"jwks_url": "https://<oidc-provider>/.well-known/jwks.json",
   "issuer": "https://<oidc-provider>/", "audience": "<api audience>"},
  {"jwks_url": "https://<identies>/.well-known/jwks.json",
   "issuer": "<TOKEN_EXCHANGE_ISSUER>", "audience": "<an audience in TOKEN_EXCHANGE_AUDIENCE>"}
]
```

The `issuer` must equal Identies' `TOKEN_EXCHANGE_ISSUER`, and the `audience` must be one of its
`TOKEN_EXCHANGE_AUDIENCE` values — and it is the audience the agent or service must request at
`/oauth/token`.

## Agent runbooks

Use the [agent endpoints](agents.md) with the product's service credential.

| Situation | Do this |
|---|---|
| **A client secret leaked** | `POST /agents/{id}/revoke` now (new tokens stop at once; already-issued tokens last up to 15 minutes), then `POST /agents/{id}/rotate` when the owner is ready and give the new secret to the agent |
| The agent's secret **expired** (`status: expired`) | `POST /agents/{id}/rotate` |
| The agent lost its credentials | `POST /agents/{id}/rotate` (a claim code only works for an **unclaimed** agent) |
| The **claim code** was lost or expired | `POST /agents/{id}/claim-codes` |
| An agent looks idle or unexpectedly busy | `GET /agents/{id}` and read `last_used_at`; revoke if it is not expected |
| An agent should no longer exist | `DELETE /agents/{id}`; the row remains as a tombstone |
| Restore a revoked agent | `POST /agents/{id}/rotate` (there is no separate un-revoke) |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `403 {"error": "Forbidden"}` on `/agents` or another service-only path | The token is not a service-account token: it is a human token, an API key, or an **agent's** token; or it lacks the `account_type` / `client_id` claims; or it is an OIDC token whose client id is not in `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS` |
| `401 {"error": "Unauthorized"}` | The token failed verification: wrong issuer or audience, wrong or rotated key, expired |
| `POST /oauth/token` → `400 Invalid audience` | The requested `audience` is not in `TOKEN_EXCHANGE_AUDIENCE` |
| `POST /oauth/token` → `401 Invalid client credentials` | Wrong secret, or the client is revoked, **expired**, deleted, or its owner is deleted |
| A consumer rejects an Identies-issued token | Identies is not a configured provider there, or the issuer/audience do not match ([above](#a-service-that-must-accept-identies-issued-tokens-agents-service-accounts)) |
| No events arrive | `NATS_ENABLED` is not `true` in Identies, or NATS is unreachable (publishing is best-effort and only logged) |
| `403 Access denied` on a management route | Custos denies `identies.<resource>` : `<action>` for that user |
| `503 Authorization service unavailable` | Custos is unreachable or erroring; check `CUSTOS_API_URL` |
| User responses fail validation for an agent | `AGENT_EMAIL_DOMAIN` is a domain the email validator rejects (`.invalid`, `.test`, `.localhost`) |
| JWKS fetch returns `403` from behind Cloudflare | See the WAF rule in [Quick Setup](quick_setup.md#jwks-jwt-verification-issues) |

## Known issues

| Issue | Impact / workaround |
|---|---|
| The SDK's authorization cache reads a different key than it writes | Do **not** set `AUTHORIZATION_CACHE_ENABLED=true`: cached entries would be read back as denied. It is off by default. Tracked in the `tessera-sdk` repository |
| `POST /external-accounts/link-tokens` has no check beyond authentication | Restrict who can reach it at the network level |
| Agents appear in `GET /service-accounts` and can be managed through it | Use `/agents`. [#171](https://github.com/tesserahq/identies/issues/171) |
| Humans cannot be deleted | Not yet implemented; `user.deleted` is published only for service accounts and agents |
| Only users are soft-deleted | [#95](https://github.com/tesserahq/identies/issues/95) |
| A still-valid JWT for a deleted user is not rejected explicitly | Resolution falls through to the OIDC provider, which rejects it. Tokens are short-lived (15 minutes) |
| Events are best-effort | No outbox; consumers must tolerate a missed event |
| `SUPER_USER_EMAIL`, `REDIS_*`, `LOG_LEVEL` are declared but unused | [Configuration](configuration.md#declared-but-unused) |
