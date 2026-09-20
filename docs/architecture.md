# Architecture

This document provides an overview of Identies' system design, core data models, and integration patterns.

## System Overview

Identies is built as a FastAPI-based microservice that provides identity and user management capabilities. It follows a repository-oriented architecture with clear separation of concerns between models, repositories, routers, and commands.

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: OIDC (OpenID Connect) JWTs, Identies-issued JWTs from OAuth client credentials, and API keys
- **Authorization**: Custos integration for RBAC
- **Dependency Management**: Poetry
- **Observability**: OpenTelemetry, Prometheus metrics, Rollbar error tracking

## Core Data Models

Every table has `created_at` and `updated_at`. Tables marked *soft-deletable* also have a
`deleted_at` column; see [Data Lifecycle](data_lifecycle.md) for what deletion actually does to each.

### User

One row per principal: a human, a service account or an [agent](agents.md). Concepts in
[Concepts](concepts.md).

**Key fields**

- `id` (UUID): primary key, and the identifier every other service uses for the user
- `kind` (String, required): `human`, `agent` or `service_account` (`CHECK`-constrained). Identies models the principal only; relationships between principals (for example which human is responsible for an agent) belong to the products that own them
- `service_account` (Boolean, **computed**): true when `kind` is `agent` or `service_account`. Kept for compatibility; prefer `kind`. The old physical column remains until [#171](https://github.com/tesserahq/identies/issues/171)
- `email` (String): required. Agents get a synthetic, non-delivering address
- `first_name`, `last_name`, `preferred_name`, `avatar_url`, `avatar_asset_id`, `theme_preference`
- `external_id` (String, optional) and `provider`: the identity from the OIDC provider (`system-...` for service accounts, `agent-...` for agents)
- `verified`, `verified_at`, `confirmed_at`
- `deleted_at`: soft delete (*soft-deletable*)

**Indexes:** `email` is unique among active users (`uq_users_email_active`, partial on `deleted_at IS NULL`); `external_id` is unique among active users where not null (`uq_users_external_id`).

### Client

An OAuth client: credentials owned by a principal ([Credentials](credentials.md#oauth-clients-and-client-credentials)).

- `client_id` (`cs_...`, unique), `secret_hash` (never the secret), `name`
- `owner_id`: the principal the client acts as (the `sub` of its tokens); `created_by_id`
- `revoked`, `expires_at` (optional), `last_used_at`
- `deleted_at` (*soft-deletable*, but deleting a client currently removes the row)

### AgentClaim

A one-time code that turns an agent into credentials ([Agents](agents.md#claim-codes)).

- `agent_user_id`, `claim_id` (public, unique), `secret_hash`
- `expires_at`, `claimed_at`, `invalidated_at`, `failed_attempts`

### ApiKey

An opaque `ak_<key_id>.<secret>` credential ([Credentials](credentials.md#api-keys)).

- `user_id`, `key_id` (unique), `secret_hash`, `name`
- `last_used_at`, `expires_at` (optional), `revoked`

### AccessRule

An invite-only rule ([Authentication](authentication.md#invite-only-access)).

- `kind` (`email` or `domain`), `value`, `note` (optional)
- Unique on `(kind, value, deleted_at)`. *Soft-deletable*, but deleting a rule currently removes the row

### ExternalAccount and LinkToken

A person's account on an outside platform, and the short-lived single-use token used to link it.

- `ExternalAccount`: `user_id`, `platform`, `external_id` (unique where not null), `data` (JSON)
- `LinkToken`: `token` (unique), `platform`, `external_id`, `data`, `expires_at`, `used_at`

### Application

A small registry entry: `name`, `url`, `logo`, `description`. *Soft-deletable*, but deleting one currently removes the row.

## Database Integration

### PostgreSQL Configuration

Identies uses PostgreSQL as its primary data store with the following features:

- **Connection Pooling**: Configurable pool size and max overflow
- **Connection Management**: Automatic reconnection with `pool_pre_ping`
- **Application Naming**: Database connections tagged with application name for monitoring
- **Transaction Management**: SQLAlchemy session-based transactions

### Database Manager

The system uses `tessera_sdk.core.database_manager.DatabaseManager` for database operations, providing:

- Centralized connection management
- Session lifecycle handling
- Migration support via Alembic

### Migration Strategy

Database schema changes are managed through Alembic migrations:

- Migrations stored in `alembic/versions/`
- Version control for schema evolution
- Rollback support for failed migrations

## Authentication & Authorization

The full description is in [Authentication](authentication.md); this is the summary.

- **Credentials**: OIDC access tokens (humans and OIDC machine-to-machine tokens), Identies-issued JWTs from OAuth client credentials, delegated tokens from token exchange, and API keys. See [Credentials](credentials.md).
- **Verification**: an `ak_` key is checked in the database; a JWT is checked against Identies' own public key first, then against the configured OIDC JWKS providers.
- **Three path classes**: public paths, **service-only** paths (a service-account token, no user), and authenticated paths. The class of every route is in the [API Reference](api_reference.md).
- **Users**: resolved from the token subject; an unknown human is onboarded from the provider's userinfo (subject to invite-only access), and an unknown OIDC machine-to-machine client is onboarded as a service account.
- **Permissions**: most authenticated routes ask [Custos](https://github.com/tesserahq/custos) whether the user may perform an `identies.<resource>` action, using the domain `*`.

Other services normally verify Identies-issued and OIDC JWTs themselves against the published keys
(the shared SDK supports several providers), and verify `ak_` API keys by calling Identies'
introspect endpoint. Each consuming service keeps its own local copy of the users it needs, kept
current from [events](events.md); how a service creates that copy is that service's concern.

## Service Layer Architecture

### Repositories

Data access, one per entity (`UserRepository`, `ClientRepository`, `ApiKeyRepository`,
`AgentRepository`, `AgentClaimRepository`, ...). **Every user lookup excludes soft-deleted rows.**

### Commands

One class per operation with a single public `execute()`. Commands own business rules and publish
events. Examples: `OnboardUserCommand`, `CreateApiKeyCommand`, `CreateClientCommand`, and for agents
`CreateAgentCommand`, `ClaimAgentCommand`, `IssueAgentClaimCommand`, `RotateAgentCredentialsCommand`,
`RevokeAgentCommand`, `DeleteAgentCommand`.

### Events

Every state change publishes a CloudEvent through the shared SDK publisher. See [Events](events.md)
for the catalog and [User Events](user_events.md) for the user projection contract.

## API Design

The complete route list, with each route's access class and Custos permission, is the generated
table in the [API Reference](api_reference.md). Routers are grouped by domain:

| Prefix | Domain |
|---|---|
| `/users`, `/internal/users`, `/me`, `/userinfo` | Users and the caller's own profile |
| `/service-accounts` | Service accounts and their API keys and clients |
| `/agents` | AI agents ([Agents](agents.md)); service only |
| `/clients`, `/oauth` | OAuth clients, `POST /oauth/token`, token exchange |
| `/api-keys`, `/me/api-keys` | API keys |
| `/access-rules` | Invite-only access rules |
| `/external-accounts` | Linking outside platform accounts |
| `/applications` | Application registry |
| `/.well-known/jwks.json`, `/livez`, `/readyz` | Keys and health |

### Responses

- Successful responses return the resource itself; lists return a page (`items`, `total`, `page`, `size`, `pages`) with offset pagination via `fastapi-pagination`.
- Errors from routes are `{"detail": ...}`; errors from the authentication middleware are `{"error": ...}`.
- `/docs` and `/redoc` are disabled; `GET /openapi.json` is served to authenticated callers only.

## Observability

### Metrics

Prometheus metrics exposed at `/metrics`:

- Request counts and durations
- Database query metrics
- Custom business metrics

### Tracing

OpenTelemetry integration for distributed tracing:

- Request tracing across services
- Database query tracing
- Custom span creation

### Logging

Structured logging with configurable levels:

- JSON-formatted logs
- Contextual information
- Error tracking via Rollbar (production)

## Security Considerations

### Secrets

- API key secrets, OAuth client secrets and agent claim secrets are **hashed**, shown once, and never returned again, logged or published in events.
- Secret comparison is constant-time.
- Claim codes are single-use, short-lived, locked after repeated wrong guesses, and every failure looks the same.

### Trust boundaries

- **Service-only paths** accept only service-account tokens. Human tokens, API keys and **agents' own tokens** are rejected. Identies only puts the service-account claims on tokens for clients owned by a `kind = service_account` principal ([Design Decisions](decisions.md#agents-must-never-act-as-a-service)).
- The agent endpoints act only on active agents; they cannot touch a human or a service account.
- `POST /api-keys/introspect` is deliberately public and has no Custos dependency, because Custos calls it.

### Tokens

- JWTs are signed RS256 with a single key published at `/.well-known/jwks.json`; there is no overlap period when it is replaced ([Operations](operations.md#signing-keys)).
- Client-credential tokens last 15 minutes, so revocation takes up to 15 minutes to reach tokens already minted.

### Data

- Parameterized queries prevent SQL injection; connection pooling limits resource exposure.
- Users are soft-deleted and their credentials revoked ([Data Lifecycle](data_lifecycle.md)).

## Tenancy

Identies is **not** multi-tenant. Custos permission checks use the single domain `*`. Tenancy
(family accounts, workspaces) is a concern of the products that use Identies.

## Development Patterns

### Testing

- Pytest for unit and integration tests
- Fixtures for test data generation
- Faker for realistic test data
- Test database isolation

### Code Organization

```
app/
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
├── repositories/    # Data access layer
├── routers/         # API endpoints
├── commands/        # Complex operations
├── events/          # Event definitions
├── middleware/      # Request middleware
└── utils/           # Utility functions
```

## Future Considerations

- GraphQL API support
- Enhanced identity provider integrations
- Advanced access control policies
- Audit logging system
- Rate limiting and throttling

