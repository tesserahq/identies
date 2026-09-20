# Agents

An **agent** is a user with `kind = agent`: an AI agent that acts under its own identity,
authenticating with OAuth **client credentials** it obtains through a one-time **claim code**. It exchanges them for short-lived JWT access tokens at `/oauth/token`.

Identies models the principal only. *Which human is responsible for an agent*, what the
agent may do, how many an owner may have and what happens when the owner is deleted are
product concerns and belong to the calling service (for example Linden).

## Who can call these endpoints

The endpoints are **privileged** and meant for a trusted service that has already
authorized the human's request. `/agents` is an M2M path in the authentication
middleware: only a service-account token from an allowed client gets through
(`ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`, or a token issued by Identies itself). Human tokens
and API keys are rejected with 403, and no human user is resolved.

## Endpoints

| Method and path | Purpose |
|---|---|
| `POST /agents` | Create an agent and its first claim code. Body: `{"name": "..."}` |
| `POST /agents/{agent_id}/claim-codes` | Issue a new code for an **unclaimed** agent; the previous code stops working. 404 if not an active agent, 409 if already claimed |
| `POST /agents/claim` | Exchange a code for the agent's client credentials. Body: `{"code": "ac_..."}` |
| `GET /agents/{agent_id}` | Lifecycle status: `unclaimed`, `active`, `revoked` or `expired`, plus `client_id`, the secret's expiry, `last_used_at` and (while unclaimed) when the open claim code expires |
| `POST /agents/{agent_id}/rotate` | Replace the client secret (returned once). Same `client_id`; the old secret stops working at once; expiry restarts. Also restores a revoked agent. 409 if not claimed yet |
| `POST /agents/{agent_id}/revoke` | Cut the agent off: its credentials (and any API key) stop working and open claim codes are invalidated. Idempotent. Returns the status |
| `DELETE /agents/{agent_id}` | Soft-delete the agent (204). Its credentials and open claim codes stop working; records it created keep resolving it |

The agent id in the paths above must belong to an **active agent**: a human, a service account, a deleted user or an unknown id is a `404`, so these endpoints can never be used to delete or cut off anyone else.

`POST /agents` returns the agent (`UserResponse`), the plaintext `claim_code` and its
`expires_at`. `POST /agents/claim` returns `client_id` (`cs_...`), `client_secret`, `user_id` and the
secret's `expires_at`. **Both secrets are returned once**; only hashes are stored.

## Agent users

- `kind = agent`, no password, `verified` at creation, external id `agent-<random>`.
- A synthetic email `agent-<id>@<AGENT_EMAIL_DOMAIN>`. It must pass email validation but
  must never deliver. The default is `agents.example`: `.example` is reserved (RFC 2606) so
  it never resolves. `.invalid`, `.test` and `.localhost` are **rejected** by the email
  validator and would break user responses and events, so do not use them.
- Identies sends no email. Anything that starts emailing users must skip `kind = agent`.
- Creating an agent publishes `user.created` (see [User Events](user_events.md)) with
  `kind: agent`. Claiming publishes `client.created` (never the secret).
- `service_account` is `true` for agents (it is computed from `kind`).

## Claim codes

- Format `ac_<claim_id>.<secret>`. The claim id is public and locates the claim; the secret
  is 32 bytes of URL-safe randomness and only its SHA-256 is stored. Compared in constant time.
- Single use. Expires after `AGENT_CLAIM_TTL_MINUTES` (default 15).
- After `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` (default 5) wrong secrets the claim is locked.
- Issuing a new code invalidates any open code for that agent.
- Claiming locks the claim row, so concurrent claims of one code mint exactly one key.
- **Every failure is the same `400`** ("Invalid or expired claim code") whether the code was
  malformed, unknown, wrong, expired, used, locked or its agent was deleted. Do not log codes.

## Authenticating as an agent

The agent calls `POST /oauth/token` (client credentials grant) with its `client_id` and
`client_secret` and receives a 15-minute RS256 JWT. The token's `sub` is the agent user's id
and it carries **no service-account claims**. Services verify it locally against the
`/.well-known/jwks.json` endpoint, so there is no per-request call back to Identies (unlike
`ak_` API keys). Downstream services must list Identies as an auth provider.

- The client secret expires after `AGENT_CLIENT_SECRET_TTL_DAYS` (default 30); an expired,
  revoked or deleted-owner client cannot mint tokens. Rotate it before then.
- **Last used:** every successful token mint records `last_used_at` on the client (a failed
  attempt does not), so an owner can spot unused or unexpected agents. It is returned by
  `GET /agents/{agent_id}`.
- **Revocation is not instant:** a revoked client can't mint new tokens, but a token already
  issued stays valid until it expires (at most 15 minutes).
- Revoke has no separate pause state: revoke cuts access, and rotating restores it.
- Deleting an agent revokes its client (see [Architecture](architecture.md)).

### Events

| Operation | Event |
|---|---|
| Create agent | `user.created` (`kind: agent`) |
| Claim | `client.created` |
| Rotate | `client.rotated` |
| Revoke | `client.revoked` (one per client that was active) |
| Delete | `user.deleted` |

None of them contain a secret.

### Agents must never act as a service

`/oauth/token` only adds the service-account claims (which open the privileged M2M endpoints,
including `/agents` and `/oauth/token-exchange`) when the client's owner is `kind =
service_account`. `service_account` is *also* true for agents, so this check uses `kind`.
Without it, an agent's own token would have passed those gates and could have created agents
or minted delegated tokens for any user. This is covered by regression tests that use real
minted tokens.

## Configuration

| Variable | Default |
|---|---|
| `AGENT_EMAIL_DOMAIN` | `agents.example` |
| `AGENT_CLAIM_TTL_MINUTES` | `15` |
| `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` | `5` |
| `AGENT_CLIENT_SECRET_TTL_DAYS` | `30` |
