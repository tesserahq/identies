# Concepts

## What Identies owns, and what it does not

| Identies owns | Someone else owns |
|---|---|
| Who exists: users, service accounts, agents | What they may do (permissions): **Custos** |
| How they prove it: credentials, tokens, claim codes | Their profile in a product, their data: the product |
| Whether a principal is active or deleted | *Relationships between principals* — who is responsible for an agent, which family account it belongs to: the product (for example Linden) |
| Events that announce identity changes | Reacting to them: each consuming service |

The last row is a deliberate boundary. Identies stores that an agent **is an agent** (`kind`),
not **whose** agent it is. See [Design Decisions](decisions.md#identies-does-not-store-who-owns-an-agent).

## Principal kinds

Every user row has a required `kind`. It replaces the pile of boolean flags that would
otherwise be needed to describe what a principal is.

| `kind` | Who it is | Created by | Authenticates with |
|---|---|---|---|
| `human` | A person | First request after signing in through the OIDC provider (onboarded automatically, subject to [invite-only](authentication.md#invite-only-access)) | An OIDC access token (JWT) |
| `service_account` | A trusted machine client (a service such as Linden or Conversa) | `POST /service-accounts`, or automatically the first time an OIDC machine-to-machine token for it is seen | Client credentials (an OIDC M2M token, or an Identies-issued JWT) or an API key |
| `agent` | An AI agent acting under its own identity | `POST /agents`, called by a trusted service on behalf of a human | Client credentials obtained by claiming a one-time code |

What differs in practice:

| | `human` | `service_account` | `agent` |
|---|---|---|---|
| Listed by `GET /users` | yes | no | no |
| Listed by `GET /service-accounts` | no | yes | yes (known gap, see [#171](https://github.com/tesserahq/identies/issues/171)) |
| May use `PUT /me` | yes | no | no |
| Token carries service-account claims | n/a | **yes** | **never** |
| May call the [service-only endpoints](authentication.md#path-classes) | no | yes (if allowed) | **never** |
| Has a password / email login | via OIDC | no | no |
| Email | real | supplied at creation (a generated address when auto-onboarded from an OIDC M2M token) | synthetic, never delivers (see [Agents](agents.md#agent-users)) |

### `kind` and the `service_account` flag

`service_account` is a **computed** value: true when `kind` is `agent` or `service_account`, so
the two can never disagree. It means "non-interactive principal" and is kept for compatibility
with existing consumers. **Prefer `kind` in new code.** The old physical column still exists,
written from `kind` and never read for behaviour; it is scheduled for removal in
[#171](https://github.com/tesserahq/identies/issues/171).

!!! warning "Agents are non-interactive but must never act as a service"
    Because `service_account` is true for agents, any check that means "is this a trusted
    machine client?" must use `kind == service_account`, not the flag. This is what stops an
    agent's own token from opening the service-only endpoints. See
    [Design Decisions](decisions.md#agents-must-never-act-as-a-service).

## Credentials at a glance

| Credential | Looks like | Lifetime | Used by |
|---|---|---|---|
| OIDC access token | JWT from the OIDC provider (Auth0) | Set by the provider | Humans; OIDC M2M service accounts |
| Identies access token | RS256 JWT from `POST /oauth/token`, `sub` = the client's owner | **15 minutes** (fixed) | Service accounts and agents that hold client credentials |
| Client credentials | `cs_<id>` + a secret | Optional expiry; agents: 30 days by default | Exchanged for an Identies access token |
| Delegated token | JWT from `POST /oauth/token-exchange` | `TOKEN_EXCHANGE_TTL_SECONDS` (default 600 s) | A trusted service acting for a user |
| API key | `ak_<key_id>.<secret>` | Optional expiry | Legacy and existing integrations |
| Claim code | `ac_<claim_id>.<secret>` | 15 minutes, single use | Handing an agent its first credentials |

Details, lifecycles and revocation are in [Credentials](credentials.md).

## Identifiers you will see

| Prefix | Meaning |
|---|---|
| `cs_` | OAuth client id |
| `ak_` | API key |
| `ac_` | Agent claim code |
| `system-...` | External id of a service account |
| `agent-...` | External id of an agent |

## Glossary

- **Principal**: anything that can act — a human, service account or agent.
- **Projection**: another service's local copy of a user row, keyed by the same Identies UUID and kept current from events ([User Events](user_events.md)).
- **Tombstone**: a soft-deleted user row that is kept so records referencing it still resolve ([Data Lifecycle](data_lifecycle.md)).
- **M2M**: machine to machine. Here it also names the paths only trusted services may call.
- **Claim**: exchanging a one-time code for an agent's credentials.
- **Custos**: the authorization service that answers "may this user do this action on this resource?".
