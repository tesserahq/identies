# Agents

An **agent** is a principal with `kind = agent`: an AI agent that acts under **its own identity**
instead of borrowing a person's. It authenticates with OAuth **client credentials** that it
receives by redeeming a one-time **claim code**, and it exchanges those for short-lived JWTs.

Identies models the principal and its credentials only. *Which human is responsible for an
agent*, what the agent may do, and how many one person may have are product decisions and live in
the calling product (for example Linden). See
[Design Decisions](decisions.md#identies-does-not-store-who-owns-an-agent).

## Who does what

| Actor | Role |
|---|---|
| **Owner** | A person who wants their agent to have access. Never talks to Identies for this |
| **Product** (e.g. Linden) | Authorizes the owner, keeps the owner-to-agent relationship, calls Identies with **its own service credential** |
| **Identies** | Creates the agent, issues and redeems claim codes, mints tokens, rotates, revokes, deletes |
| **Agent** | Redeems the code (through the product or its CLI) and then uses its client credentials |

## The flow

```
 Owner            Product (Linden)                  Identies                     Agent
   │  "invite agent"     │                              │                          │
   │────────────────────►│  POST /agents {name}         │                          │
   │                     │─────────────────────────────►│ creates agent + claim    │
   │                     │◄─────────────────────────────│ agent, claim_code (once) │
   │◄────────────────────│  shows the code              │                          │
   │  gives code to agent│                              │                          │
   │─────────────────────────────────────────────────────────────────────────────►│
   │                     │◄──────────── redeem code ────────────────────────────── │
   │                     │  POST /agents/claim {code}   │                          │
   │                     │─────────────────────────────►│ creates OAuth client     │
   │                     │◄─────────────────────────────│ client_id, secret (once) │
   │                     │──────────────────────────── credentials ───────────────►│
   │                     │                              │◄── POST /oauth/token ────│
   │                     │                              │─── 15-minute JWT ───────►│
   │                     │◄───────────────── API calls with the JWT ───────────────│
```

The product calls the `/agents` endpoints with **its own** token; the agent only ever calls
`/oauth/token` and then the product's API.

## Who can call the endpoints

All `/agents` endpoints are **service only**: they require a service-account token. Human tokens,
API keys and — importantly — **an agent's own token** are rejected with `403`. Identies only puts
the required claims on tokens for clients owned by a `kind = service_account` principal, never for
an agent. Details in [Authentication](authentication.md#the-service-only-gate).

Every id in a path must belong to an **active agent**. A human, a service account, a deleted user
or an unknown id is a `404`, so these endpoints can never be used to delete or cut off anyone else.

## Endpoints

### Create: `POST /agents`

```http
POST /agents
{ "name": "Claude" }
```

```json
{
  "agent": { "id": "…", "kind": "agent", "first_name": "Claude", "last_name": "Agent",
             "email": "agent-<id>@agents.example", "service_account": true, "…": "…" },
  "claim_code": "ac_<claim_id>.<secret>",
  "expires_at": "2026-09-22T10:15:00Z"
}
```

Creates the agent and its first claim code in one transaction. Publishes `user.created`.
`name` is 1–100 characters and becomes the agent's first name.

### Redeem: `POST /agents/claim`

```http
POST /agents/claim
{ "code": "ac_<claim_id>.<secret>" }
```

```json
{ "client_id": "cs_…", "client_secret": "…", "user_id": "<agent id>", "expires_at": "2026-10-22T10:00:00Z" }
```

Creates the agent's OAuth client and returns its credentials **once**. Publishes `client.created`.
Every failure — malformed, unknown, wrong, expired, already used, locked, or the agent was
deleted — is the **same** `400 {"detail": "Invalid or expired claim code"}`, so a caller cannot
learn which it was. Never log a claim code.

### New code: `POST /agents/{agent_id}/claim-codes`

Issues a new code for an **unclaimed** agent; the previous code stops working. `404` if not an
active agent; `409` if the agent has already been claimed (rotate instead).

### Status: `GET /agents/{agent_id}`

```json
{ "agent": { "…": "…" }, "status": "active", "client_id": "cs_…",
  "client_expires_at": "2026-10-22T10:00:00Z", "last_used_at": "2026-09-23T08:30:00Z",
  "claim_expires_at": null }
```

`status` is one of `unclaimed`, `active`, `revoked`, `expired` ([lifecycle](data_lifecycle.md#agent-lifecycle)).
`last_used_at` is when the credentials last minted a token (failed attempts do not count), so an
owner can spot an agent that is idle or unexpectedly busy. `claim_expires_at` is set only while
unclaimed. The response never contains a secret.

### Rotate: `POST /agents/{agent_id}/rotate`

Returns new credentials (same shape as claim, **same `client_id`**, new secret shown once).
The old secret stops working immediately, the expiry restarts, and a **revoked or expired** agent
is restored. `409` if the agent has not been claimed. Publishes `client.rotated`.

### Revoke: `POST /agents/{agent_id}/revoke`

Cuts the agent off: its clients (and any API key) are revoked and open claim codes are
invalidated. Idempotent. Returns the status. Publishes `client.revoked` for each client that was
active. Rotate to restore access — there is no separate pause state.

### Delete: `DELETE /agents/{agent_id}`

`204`. Soft-deletes the agent ([Data Lifecycle](data_lifecycle.md)): credentials and open claim
codes stop working, records that reference the agent keep resolving it. Publishes `user.deleted`.

## Agent users

- `kind = agent`, no password, marked verified at creation, external id `agent-<random>`.
- `service_account` is `true` (computed from `kind`), so agents are hidden from `GET /users` and cannot use `PUT /me`.
- **Email:** a synthetic `agent-<id>@<AGENT_EMAIL_DOMAIN>`. It must pass email validation but never deliver. The default is `agents.example`; `.example` is a reserved TLD that never resolves. `.invalid`, `.test` and `.localhost` **do not work**: the email validator rejects them, which would break every user response and event for the agent.
- Identies sends no email. Anything that starts emailing users must skip `kind = agent`.
- Creating an agent publishes `user.created` with `kind: agent` ([Events](events.md#agent-operations)); every consumer of that event must accept the synthetic address.

## Claim codes

- Format `ac_<claim_id>.<secret>`. The claim id is public and locates the claim; the secret is 32 bytes of URL-safe randomness. Only a SHA-256 of the secret is stored, and it is compared in constant time.
- **Single use**, valid for `AGENT_CLAIM_TTL_MINUTES` (15).
- **Locked** after `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` (5) wrong secrets.
- Issuing a new code invalidates any open one for that agent.
- Redeeming locks the claim row, so concurrent attempts to redeem one code create **exactly one** client. This is covered by a test that races real database sessions.
- Public rate limiting of the redeem call is the calling product's job; the lock above is in addition to it.

## Authenticating as an agent

The agent exchanges its client credentials at `POST /oauth/token` (JSON body) for an RS256 JWT
that lasts 15 minutes:

```http
POST /oauth/token
{ "grant_type": "client_credentials", "client_id": "cs_…", "client_secret": "…",
  "audience": "https://identies.tessera.com/" }
```

The token's `sub` is the **agent's user id**, and it carries **no service-account claims**.
Services verify it locally against `/.well-known/jwks.json`, so there is no per-request call to
Identies (unlike API keys). The audience must be one of `TOKEN_EXCHANGE_AUDIENCE` **and** one the
consuming service is configured to accept.

## Security properties

| Property | How it is enforced |
|---|---|
| An agent can never act as a service | Service-account claims are minted only for `kind = service_account` owners; regression tests use **real minted tokens** through the real middleware |
| Endpoints cannot touch non-agents | Every command looks the id up as an active agent first; tests fail if that check is removed |
| Secrets are never stored or published | Claim secrets and client secrets are hashed; events and status responses contain none |
| Claim codes cannot be guessed or raced | 256-bit secret, constant-time compare, lockout, row lock |
| Deleted agents stop working | Deleting revokes clients; `/oauth/token` and validation also reject a deleted owner |
| Compromise has a bounded window | Secrets expire in 30 days; tokens last 15 minutes |

!!! warning "Revocation is not instant"
    Revoking, rotating or deleting stops **new** tokens at once, but a token already minted stays
    valid until it expires — up to 15 minutes.

## Errors

| Situation | Status |
|---|---|
| Not a service-account token | `403` `{"error": "Forbidden"}` |
| No token | `401` |
| Invalid, expired, used or locked claim code | `400` (always the same body) |
| Agent id is not an active agent | `404` |
| `claim-codes` for a claimed agent; `rotate` for an unclaimed one | `409` |
| Invalid request body (for example an empty `name`) | `422` |

## Configuration

| Variable | Default |
|---|---|
| `AGENT_EMAIL_DOMAIN` | `agents.example` |
| `AGENT_CLAIM_TTL_MINUTES` | `15` |
| `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` | `5` |
| `AGENT_CLIENT_SECRET_TTL_DAYS` | `30` |

To let a product call these endpoints, give its service account an OAuth client and, if it uses an
OIDC machine-to-machine token instead, list its client id in `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`.
Runbooks (a leaked secret, an agent that stopped working) are in [Operations](operations.md#agent-runbooks).
