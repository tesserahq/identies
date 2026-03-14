# Architecture

This document provides an overview of Identies' system design, core data models, and integration patterns.

## System Overview

Identies is built as a FastAPI-based microservice that provides identity and user management capabilities. It follows a repository-oriented architecture with clear separation of concerns between models, repositories, routers, and commands.

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: OIDC (OpenID Connect) with JWT tokens
- **Authorization**: Custos integration for RBAC
- **Dependency Management**: Poetry
- **Observability**: OpenTelemetry, Prometheus metrics, Rollbar error tracking

## Core Data Models

### User Model

The `User` model represents both regular users and service accounts in the system.

**Key Fields:**
- `id` (UUID): Primary key
- `email` (String): Unique email address
- `first_name`, `last_name` (String): User's name
- `external_id` (String, optional): ID from external identity provider
- `provider` (String, optional): Identity provider name (e.g., "google", "github")
- `verified` (Boolean): Email verification status
- `service_account` (Boolean): Flag indicating if this is a service account
- `avatar_url`, `avatar_asset_id` (String, optional): Avatar image references
- `theme_preference` (String): UI theme preference

**Relationships:**
- One-to-many with `ApiKey` (users can have multiple API keys)

**Indexes:**
- Unique index on `external_id` (where not null)
- Unique constraint on `email`

### ApiKey Model

API keys provide programmatic access to the system.

**Key Fields:**
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to User
- `key_id` (String): Unique identifier for the key
- `secret_hash` (String): Hashed secret (never stored in plain text)
- `name` (String): Human-readable name for the key
- `last_used_at` (DateTime, optional): Timestamp of last usage
- `expires_at` (DateTime, optional): Expiration timestamp
- `revoked` (Boolean): Revocation status

**Relationships:**
- Many-to-one with `User`

**Indexes:**
- Unique index on `key_id`
- Index on `user_id` for efficient lookups

### AccessRule Model

Access rules control invite-only access to the system.

**Key Fields:**
- `id` (UUID): Primary key
- `kind` (String): Type of access rule (e.g., "email", "domain")
- `value` (String): The rule value (e.g., email address or domain)
- `note` (String, optional): Administrative note

**Indexes:**
- Unique composite index on `(kind, value)`

**Features:**
- Supports soft deletion via `SoftDeleteMixin`
- Timestamp tracking via `TimestampMixin`

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

### OIDC Integration

Identies integrates with OpenID Connect providers (such as Auth0) for authentication:

- **Token Verification**: JWT tokens verified using RS256 algorithm
- **User Onboarding**: Automatic user creation from OIDC userinfo
- **Identity Resolution**: Links external identities to local user records
- **Provider Support**: Multiple identity providers (Google, GitHub, etc.)

### Token Validation Service

Identies serves as the central token validation service for the entire platform. It is responsible for communicating with external identity providers (Auth0 in production) to validate incoming JWT tokens.

**Token Validation Flow:**

1. **External Provider Communication**: Identies is the sole service that communicates directly with the external identity provider (Auth0) to validate tokens
2. **Token Validation**: When a token is received, Identies validates it against the provider's public keys and verifies its signature, expiration, and claims
3. **User Onboarding**: If the token is valid and the user doesn't exist in Identies' database, the user is automatically onboarded with information from the provider's userinfo endpoint
4. **Response**: Identies returns either a success response (token is valid) or an error response (token is invalid, expired, or malformed)

**Service Integration Pattern:**

Other services in the ecosystem (such as Custos, Sendly, etc.) use Identies as their token validation authority:

1. **Token Validation**: When a service receives a request with a JWT token, it directly validates the token against the public keys of the external authentication provider (such as Auth0).
2. **User Extraction**: After validation, the service extracts the user ID from the token's claims.
3. **User Onboarding Request**: If the user ID does not exist in the local database, the service sends a request to Identies to onboard the user.
4. **Onboarding Response**: Identies processes the onboarding and responds with either:
   - **Success**: The user is onboarded and available for future requests
   - **Error**: Onboarding failed due to invalid, expired, or malformed token or other issues
5. **Subsequent Requests**: For future requests, if the user exists locally, the service proceeds without contacting Identies. Only if the user is not found locally does it repeat the onboarding request to Identies.

This pattern provides several benefits:
- **Centralized Validation**: Single source of truth for token validation
- **Reduced Load**: Services cache user information locally after initial validation
- **Consistency**: All services use the same validation logic and user data
- **Simplified Integration**: Services don't need to integrate directly with Auth0

### Custos Integration

Authorization is handled through [Custos](https://github.com/tesserahq/custos), a separate authorization service:

- **RBAC**: Role-Based Access Control
- **Permission Evaluation**: Centralized permission checking
- **Service Communication**: API-based integration with Custos service

### Authentication Middleware

The `AuthenticationMiddleware` processes incoming requests:

1. Extracts and validates JWT tokens
2. Fetches user information from OIDC provider
3. Onboards new users automatically
4. Attaches user context to requests

## Service Layer Architecture

### Service Pattern

Services encapsulate business logic and database operations:

- **UserService**: User CRUD operations and queries
- **ApiKeyService**: API key management and validation
- **AccessRuleService**: Access rule evaluation and management

### Command Pattern

Commands handle complex operations with side effects:

- **OnboardUserCommand**: User onboarding with validation
- **CreateApiKeyCommand**: API key generation with secure hashing
- **UpdateUserCommand**: User profile updates

### Event System

Events are emitted for important state changes:

- **User Events**: User creation, updates
- **API Key Events**: Key creation, revocation
- **Service Account Events**: Service account lifecycle

## API Design

### Router Structure

Routers organize endpoints by domain:

- `/users`: User management endpoints
- `/api-keys`: API key management
- `/service-accounts`: Service account operations
- `/access-rules`: Access rule management
- `/me`: Current user information
- `/userinfo`: OIDC-compatible userinfo endpoint

### User router (`app/routers/user_router.py`)

The **User router** groups endpoints related to reading users and managing a user's API keys.

#### Endpoints

- **GET** `/users/{user_id}`: Fetch a user by ID (RBAC-protected).
- **GET** `/users`: List users (RBAC-protected, paginated).
- **GET** `/users/{user_id}/api-keys`: List API keys for a user (RBAC-protected, paginated).
- **POST** `/users/{user_id}/api-keys`: Create an API key for a user (RBAC-protected).
- **GET** `/internal/users/{user_id}`: Fetch a user by ID (**internal, service-account-only**; see below).

#### Internal endpoint: `GET /internal/users/{user_id}` (service accounts only)

This endpoint is intended to be called **only by Auth0 service accounts** using **Client Credentials (M2M) tokens**.

- **Why**: Access to `/internal/*` endpoints is restricted based on **JWT claims** that identify the caller as a service account (not an end user).
- **How**: Auth0 issues M2M access tokens and an Auth0 Action adds **custom claims** to those tokens, including an `account_type` claim set to `service_account`.
- **Note**: The code changes that enforce this claim-based restriction are not implemented yet; this is the intended contract and should be relied on by internal consumers.

Auth0 Action (Client Credentials exchange) used for M2M tokens:

```javascript
/**
* Handler that will be called during the execution of a Client Credentials exchange.
*
* @param {Event} event - Details about client credentials grant request.
* @param {CredentialsExchangeAPI} api - Interface whose methods can be used to change the behavior of client credentials grant.
*/
exports.onExecuteCredentialsExchange = async (event, api) => {
  api.accessToken.setCustomClaim(
    "https://mylinden.family/client_id",
    event.client.client_id
  );

  api.accessToken.setCustomClaim(
    "https://mylinden.family/client_name",
    event.client.name
  );

  api.accessToken.setCustomClaim(
    "https://mylinden.family/account_type",
    "service_account"
  );
};
```

### Response Format

All API responses follow a consistent format:

```json
{
  "data": [...]
}
```

### Pagination

List endpoints support pagination via `fastapi-pagination`:

- Configurable page size
- Cursor-based or offset-based pagination
- Metadata included in responses

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

### API Key Security

- Secrets are hashed using secure algorithms
- Keys never returned in API responses
- Revocation support for compromised keys
- Expiration dates for temporary access

### Database Security

- Parameterized queries prevent SQL injection
- Connection pooling limits resource exposure
- Soft deletes preserve audit trails

### Authentication Security

- JWT token validation with signature verification
- Token expiration enforcement
- Secure secret management via environment variables

## Multi-Tenancy

The system is designed to support multi-tenant scenarios:

- Workspace-scoped resources
- Tenant isolation at the application layer
- URL-based tenant identification (not payload-based)

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

