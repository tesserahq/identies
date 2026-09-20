# Design Decisions

The reasoning behind how Identies works, including what was considered and rejected. Add an entry
when you make a decision someone might later want to reverse. Each entry says what was decided,
why, and what it costs.

## `kind` instead of more flags

**Decision.** Every user has a required `kind`: `human`, `agent` or `service_account`.

**Why.** Agents needed to be told apart from humans and from trusted machine clients. A second
boolean next to `service_account` would have made the meaning of the combinations ambiguous, and
every consumer would need to learn them. One enum says what a principal is.

**Cost.** Downstream services that need to treat agents differently must read `kind` (it is an
additive field on every `user.*` event, and a missing value means `human`). The change was made
with a backfill and a `CHECK` constraint so a null or unknown kind is impossible at the database.

## `service_account` is computed from `kind`

**Decision.** `service_account` is true when `kind` is `agent` or `service_account`, and is
computed, not stored as a source of truth. The old column is kept for one release and dropped in
[#171](https://github.com/tesserahq/identies/issues/171).

**Why.** Two stored fields describing the same thing can disagree. Computing one from the other
removes that. Keeping the column briefly means a rolling deploy does not break old code.

**Cost.** The flag now means "non-interactive principal", which no longer matches its name.
That is why any check for *trusted machine client* must use `kind`
([below](#agents-must-never-act-as-a-service)).

## Identies does not store who owns an agent

**Decision.** Identies stores that an agent **is** an agent, not **whose** agent it is. The owner,
the per-owner limit, role changes and the "agent of X" attribution live in the calling product.

**Why.** The relationship is really "this agent belongs to this family account, administered by
this person", which is a membership — product data that Identies does not have. Every rule that
uses the owner (limits, cascade on owner deletion, who may upgrade the agent) is a product rule.
Identies never needs the owner to do its own work. Storing it in the shared identity service
would couple it to one product and create two sources of truth to keep in sync.

**Cost.** If a human is deleted directly in Identies without going through the product, their
agents are not cascaded by Identies. The product handles the cascade and runs a reconciliation
sweep as a backstop. A nullable owner column could be added later without breaking anything;
removing one is much harder.

## Agents use client credentials, not API keys

**Decision.** Claiming an agent creates an OAuth client and returns `client_id` and
`client_secret`. The agent exchanges them for a 15-minute JWT.

**Why.** API keys are verified by calling Identies' introspect endpoint on every request, which
creates a dependency and latency on every call across the platform (and a circular dependency
with Custos). JWTs verify locally against the published key. The platform is also moving away from
`ak_` keys, and existing production services already trust Identies-issued JWTs.

**Cost.**

- **Revocation is not instant.** A revoked client cannot mint new tokens, but a token already minted stays valid for up to 15 minutes.
- Clients must mint and refresh tokens, which is more work than storing a static key.
- A long-lived self-contained JWT used *as* an API key was considered ([#122](https://github.com/tesserahq/identies/issues/122)) and rejected for agents: it has the same revocation problem with a much longer window.

## Agents must never act as a service

**Decision.** Service-account claims are minted only for clients owned by a `kind = service_account`
principal. Agents never get them.

**Why.** This was found while building agents. `/oauth/token` added those claims whenever the
client's owner had `service_account = true`. Once `service_account` was computed and true for agents,
an agent's own token passed the service-only gate, which trusts any Identies-issued token that
carries those claims. That would have let an agent create more agents and mint delegated tokens for
**any user** through token exchange. It was reproduced with real minted tokens before being fixed.

**Consequence.** The rule is enforced in one place and guarded by regression tests that mint real
tokens and run them through the real middleware for every service-only endpoint. Any new
"trusted service" check must use `kind`, never the flag.

## The synthetic agent email uses `agents.example`

**Decision.** Agents get `agent-<id>@agents.example` (configurable).

**Why.** The user model requires a valid, unique email. Email sub-addressing (`me+agent@…`) was
rejected: not every provider supports it, the agent has no mailbox, and uniqueness becomes fragile.
The obvious non-deliverable choice, `.invalid`, does **not** work: the email validator rejects
`.invalid`, `.test` and `.localhost`, which would have broken every user response and event for an
agent. `.example` is a reserved TLD that never resolves, and it validates.

**Cost.** Every consumer that validates emails must accept the domain; a test guards it.

## Claim codes

**Decision.** A claim code is `ac_<claim_id>.<secret>`: a public id that locates the claim and a
256-bit secret of which only a hash is stored. It is single use, lives 15 minutes, locks after five
wrong secrets, and every failure returns the same generic error. Redeeming locks the row.

**Why.** The endpoint is reachable by anyone holding a guess, so it must not reveal whether a code
exists, must be expensive to brute-force, and must not mint two credentials from one code when
requests race.

**Cost.** A lost code cannot be recovered, only replaced.

## The agent endpoints are privileged operations, not owner-facing

**Decision.** `/agents` is service only. The product authorizes the owner and then calls
Identies with its own credential; Identies does not know who the owner is.

**Why.** Identies cannot decide whether a given person may invite an agent to a given family
account — the product can. Keeping owner authorization out of Identies avoids duplicating that
model here.

**Cost.** The product is trusted to authorize correctly. Identies limits the blast radius by
acting only on active agents (never humans or service accounts) and by refusing agents' own tokens.

## Users are soft-deleted; credentials die with them

**Decision.** Deleting a user sets `deleted_at` and keeps the row. Their API keys and clients are
revoked, validation also rejects a deleted owner, and email and external id uniqueness apply only to
active users.

**Why.** Other services hold records that reference the user's id; a hard delete would orphan
them. A deleted agent must still show up as the creator of what it made. The partial unique indexes
let an email be reused.

**Cost.** Every user lookup must exclude deleted rows (there is no automatic filter). Only users
are soft-deleted so far ([#95](https://github.com/tesserahq/identies/issues/95)).

## Service-only paths are gated by claims and an allowlist

**Decision.** A small set of paths (`/internal/users`, `/oauth/token-exchange`, `/agents`) require
a service-account token and resolve no user. OIDC machine-to-machine tokens must also be on
`ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`; Identies-issued ones are trusted by signature.

**Why.** These operations must not be reachable with a person's token or an API key. They act on
behalf of the platform rather than a person, so no user is resolved and no Custos permission applies.

**Cost.** Anything that can obtain an Identies-issued service-account token is trusted, so creating
a client for a service account is itself a privileged act.

## User events are a full projection contract

**Decision.** `user.created`, `user.updated` and `user.deleted` carry a complete projection body,
including `id`, `kind` and timestamps, and are the **only** events for users and service accounts.
The older `service_account.*` events were removed.

**Why.** Other services keep a local copy of users keyed by the Identies id. The old payload
dropped the id, so a consumer could not upsert from the payload alone. Two event families for the
same thing would have forced consumers to subscribe to both.

**Cost.** Delivery is best-effort with no outbox, so consumers must tolerate a missed event.

## Revocation is bounded, not instant

**Decision.** Client-credential tokens last 15 minutes and are verified locally, so revoking,
rotating or deleting takes effect for **new** tokens immediately and for existing tokens within 15
minutes.

**Why.** The alternative — checking a revocation list on every request — brings back the
per-request dependency on Identies that JWTs exist to remove. Short lifetimes bound the exposure
without it.

**Cost.** A leaked secret can be used for up to 15 minutes after it is revoked (using tokens
already minted). The [runbook](operations.md#agent-runbooks) accounts for this.
