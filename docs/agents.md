# Agents

An **agent** is a user with `kind = agent`: an AI agent that acts under its own identity,
authenticating only with an API key it obtains through a one-time **claim code**.

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
| `POST /agents/claim` | Exchange a code for the agent's API key. Body: `{"code": "ac_..."}` |

`POST /agents` returns the agent (`UserResponse`), the plaintext `claim_code` and its
`expires_at`. `POST /agents/claim` returns `api_key` (`ak_<key_id>.<secret>`), `user_id`
and the key's `expires_at`. **Both secrets are returned once**; only hashes are stored.

## Agent users

- `kind = agent`, no password, `verified` at creation, external id `agent-<random>`.
- A synthetic email `agent-<id>@<AGENT_EMAIL_DOMAIN>`. It must pass email validation but
  must never deliver. The default is `agents.example`: `.example` is reserved (RFC 2606) so
  it never resolves. `.invalid`, `.test` and `.localhost` are **rejected** by the email
  validator and would break user responses and events, so do not use them.
- Identies sends no email. Anything that starts emailing users must skip `kind = agent`.
- Creating an agent publishes `user.created` (see [User Events](user_events.md)) with
  `kind: agent`. Claiming publishes `api_key.created`.
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

## API keys

Keys minted by a claim expire after `AGENT_API_KEY_TTL_DAYS` (default 30). Key validation
also rejects keys of deleted users (see [Architecture](architecture.md)). Rotating,
revoking and deleting agents is a separate slice.

## Configuration

| Variable | Default |
|---|---|
| `AGENT_EMAIL_DOMAIN` | `agents.example` |
| `AGENT_CLAIM_TTL_MINUTES` | `15` |
| `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` | `5` |
| `AGENT_API_KEY_TTL_DAYS` | `30` |
