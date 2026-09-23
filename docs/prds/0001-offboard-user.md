## Problem Statement

Today there is no way to remove a user from the platform. When someone should be offboarded (they leave an organization, their access should be revoked, etc.), an admin has no supported action to take — the user record stays active forever, they can still authenticate through Auth0, and no other service on the platform (billing, workspace services, etc.) is ever told the person is gone. There is dead/unused code in the codebase (`build_user_deleted_event`, an unused `UserRepository.delete_user` hard-delete) that hints this was anticipated but never finished, and no abstraction exists for talking to Auth0 at all.

Deleting a user is not a single-step action: it has to be reflected locally, revoked at the identity provider (Auth0), and broadcast to the rest of the distributed platform so other services can react — and doing all of that irreversibly and instantly, with no safety margin, is risky for an admin action that's easy to trigger by mistake or with incomplete information (e.g. not knowing about a pending billing balance).

## Solution

Introduce an **offboarding** flow for users, owned entirely by Identies, decoupled from every other service on the platform:

- An admin (self-service by the user themselves is an explicit future phase, not built now) schedules a user's offboarding, optionally choosing when it should take effect. If no time is given, it defaults to 24 hours out.
- Scheduling is non-destructive: nothing happens to the user's data or access immediately. A `user.offboarding_scheduled` event is published so other systems (e.g. a Slack notifier) can surface that an offboarding is coming.
- Until the scheduled time arrives, the offboarding can be cancelled outright via a dedicated endpoint — trivial, because nothing irreversible has happened yet.
- When the scheduled time arrives, a background job executes the offboarding: the user is soft-deleted locally, deleted from Auth0 through a new identity-provider abstraction, and a `user.deleted` event is published so downstream services can react (e.g. purge their own data associated with the user).
- Execution is the point of no return — there is no "undo" after this step, because downstream services will have already acted on the event and their state can't be un-purged.
- Identies does not ask any other service for permission to offboard a user, and does not wait for confirmation that any service has acted on the event. It notifies; it does not coordinate a distributed transaction. Any pre-offboarding business check (e.g. "does this user have an outstanding bill") is the offboarding admin's responsibility, not something Identies enforces.
- Service accounts are excluded from offboarding entirely; they have their own lifecycle via API key revocation.

## User Stories

1. As an admin, I want to schedule a user for offboarding, so that their access and data are removed from the platform without me having to manually clean up multiple systems.
2. As an admin, I want offboarding to default to a 24-hour delay if I don't specify a time, so that I have a built-in safety window even if I forget to think about timing.
3. As an admin, I want to choose a custom future time for offboarding to take effect, so that I can coordinate the action with other operational needs (e.g. end of a contract, end of a pay period).
4. As an admin, I want to cancel a scheduled offboarding before it executes, so that I can correct a mistake or a change of plans without any lasting effect on the user.
5. As an admin, I want to be notified (e.g. via Slack) when an offboarding is scheduled, so that other stakeholders have a chance to object or prepare before it becomes irreversible.
6. As a downstream service owner (e.g. billing, workspace services), I want to receive a `user.deleted` event when a user is actually offboarded, so that my service can purge or archive the data it holds about that user.
7. As a downstream service owner, I want the `user.deleted` event to only fire once the offboarding is truly final (past the grace period), so that I don't purge data for an offboarding that gets cancelled.
8. As a platform maintainer, I want user deletion in Auth0 to go through an abstraction rather than a direct Auth0 SDK call, so that the identity provider can be swapped in the future without rewriting the offboarding flow.
9. As a platform maintainer, I want the offboarding execution job to actually remove the user from Auth0 (not just locally), so that an offboarded user cannot still authenticate.
10. As a platform maintainer, I want the local user record to be soft-deleted (not hard-deleted) at execution time, so that an audit trail of who was offboarded and when is preserved.
11. As a platform maintainer, I want offboarding to never require Identies to query other services (e.g. billing) before proceeding, so that Identies stays decoupled from every other service's domain logic and doesn't become a distributed-transaction coordinator.
12. As a platform maintainer, I want service accounts to be rejected from offboarding requests, so that this human-offboarding flow doesn't collide with the separate API-key-based lifecycle service accounts already have.
13. As a platform maintainer, I want a periodic reconciliation job that retries publishing `user.deleted` if the initial publish to NATS failed, so that a transient NATS outage doesn't silently leave a soft-deleted user un-announced to the rest of the platform.
14. As a platform maintainer, I want it to be explicit and documented that Identies cannot guarantee a downstream service actually received/processed the `user.deleted` event (core NATS has no delivery guarantee), so that this known platform limitation isn't mistaken for a bug in this feature.
15. As a developer extending this system later, I want the `IdentityProvider` interface to expose only `delete_user`, so that the abstraction isn't over-built for operations nobody needs yet.
16. As an admin, I want offboarding requests for a user that is already scheduled to be handled predictably (e.g. rejected or replacing the existing schedule), so that I don't end up with ambiguous or conflicting offboarding state.

## Implementation Decisions

**Data model**
- `User` gains `SoftDeleteMixin` (already exists in `app/models/mixins.py`, used by `Client`/`Application`/`AccessRule`) to support soft-delete at execution time.
- `User` gains scheduling fields directly on the model (no separate table — only one offboarding can be pending per user at a time, this is a single lifecycle, not a history log): `offboarding_scheduled_at`, `offboarding_scheduled_by` (the admin/user id who requested it), `deleted_event_published_at` (nullable, set once the `user.deleted` publish succeeds — used by the reconciliation job).
- Service accounts (`service_account = true`) are rejected from offboarding at the command layer.

**Offboarding lifecycle (commands)**
- `ScheduleOffboardingCommand`: validates the target isn't a service account and isn't already scheduled, sets `offboarding_scheduled_at` (defaulting to now + 24h if not provided) and `offboarding_scheduled_by`, publishes `user.offboarding_scheduled`. This step is non-destructive.
- `CancelOffboardingCommand`: clears the scheduling fields. Only valid while `offboarding_scheduled_at` is still in the future / not yet executed.
- `ExecuteOffboardingCommand`: the point of no return. Soft-deletes the `User`, calls `IdentityProvider.delete_user(external_id)` to remove the user from Auth0, publishes `user.deleted`, and records `deleted_event_published_at` on success. No block-then-delete two-step in Auth0 — the grace period already happened before this runs, so execution deletes directly.

**Background execution**
- Celery is introduced to this repo for the first time (no task queue infra exists today), following the pattern already established in the `linden-family/orcha` repo: `@celery_app.task` decorators with explicit `name=`, manual `try/except` + logging for error handling (no built-in `autoretry_for`/backoff), a separate worker entrypoint/process from the API (`uvicorn` stays API-only), and `celery_app.conf.beat_schedule` for periodic tasks.
- `opentelemetry-instrumentation-celery` is added alongside Celery so worker tasks are traced consistently with the rest of the OTel-instrumented stack.
- Two beat-scheduled tasks:
  - Execution task, every 5 minutes: finds users where `offboarding_scheduled_at <= now` and not yet executed, calls `ExecuteOffboardingCommand` per user.
  - Reconciliation task, hourly: finds soft-deleted users where `deleted_event_published_at IS NULL`, retries publishing `user.deleted` for them. This only covers the `Identies → NATS broker` publish step failing (e.g. NATS was down); it explicitly does not and cannot guarantee a downstream consumer received or processed the event, since the platform's NATS usage is core NATS (no JetStream, no durable consumers, at-most-once delivery) — this is a known platform-wide limitation, not something this feature can close.

**Identity provider abstraction**
- New module area `app/services/identity_providers/`, containing:
  - An `IdentityProvider` interface (Protocol/ABC) scoped deliberately narrow: `delete_user(external_id: str) -> None`. Not broadened to cover create/update/lookup, since nothing in this feature needs those and speculative surface would be unused.
  - `Auth0IdentityProvider`, the concrete implementation, calling Auth0's Management API (client-credentials grant, cached token) to hard-delete the user by their Auth0 user id (the existing `external_id` field on `User`).
  - A `get_identity_provider()` factory that reads config to decide which implementation to return, so calling code (the execute command) never imports `Auth0IdentityProvider` directly — this is what keeps the "swap providers later" goal real rather than nominal.
- New Auth0 Management API credentials/config needed (domain, client id/secret for the Management API application, distinct from the existing OIDC login config already in `app/config.py`).

**Events**
- Revives the existing but currently unused `USER_DELETED` / `build_user_deleted_event` in `app/events/user_events.py`.
- Adds a new `USER_OFFBOARDING_SCHEDULED` event type and `build_user_offboarding_scheduled_event` builder, following the same `<entity>.<verb>` naming convention already used across `client_events.py`, `access_rule_events.py`, etc.

**API surface**
- New endpoints on the user resource for scheduling and cancelling offboarding (exact routes/verbs to be finalized in the design doc — e.g. something like a sub-resource on `/users/{id}`), admin-only for this phase. Self-service (a user offboarding themselves) is explicitly a future phase and not built now.

**Cross-service coordination**
- Identies never performs synchronous precondition checks against other services (e.g. billing) before offboarding. It is a notify-only publisher; any pre-offboarding business validation is a separate, out-of-band admin process.

## Testing Decisions

Good tests here exercise external behavior (given these inputs/state, what does the command produce or call), not internal implementation details — consistent with the existing command tests in this repo (e.g. `tests/app/commands/service_accounts/test_create_service_account_command.py`, `test_delete_service_account_command.py`), which are plain pytest functions using a real `db: Session` fixture (transaction rolled back per test, `tests/conftest.py:113`) and fixtures from `tests/fixtures/*.py`.

Modules to test:
- `IdentityProvider` / `Auth0IdentityProvider`: no HTTP-client-wrapper test pattern exists yet in this repo (`app/services` is currently empty, no `respx`/`httpx_mock` usage anywhere) — this feature introduces that pattern. Auth0's Management API HTTP calls should be mocked (via `respx` or `httpx_mock`, or `unittest.mock.patch` on the underlying call, mirroring the `patch(...)` style already used in `tests/app/middleware/auth/test_user_handler.py` and `tests/conftest.py:32`) so tests don't hit real Auth0. Cover: successful delete, Auth0 returning a not-found/already-deleted response, and a hard failure (network/5xx) propagating as an exception rather than being silently swallowed.
- `ExecuteOffboardingCommand`: the highest-risk module — cover soft-delete happening, Auth0 delete being invoked with the right `external_id`, the `user.deleted` event being published with correct payload, `deleted_event_published_at` being set on success, and the NATS publish failure path (should log and leave `deleted_event_published_at` null, matching the existing swallow-and-log pattern used by other commands like `delete_client_command.py`).
- `ScheduleOffboardingCommand`: default 24h scheduling when no time given, rejection of service accounts, rejection of an already-scheduled user, `user.offboarding_scheduled` event payload.
- `CancelOffboardingCommand`: clears fields correctly, and rejects cancelling something already executed.

Celery tasks themselves (the beat-scheduled wrappers) stay thin and are tested lightly if at all — the substantive logic lives in the commands they call, which are the actual test targets.

## Out of Scope

- Self-service offboarding (a user deleting their own account) — explicitly phase 2.
- Any synchronous cross-service precondition check (e.g. querying billing for outstanding balance) before allowing offboarding.
- Guaranteeing that a downstream service actually received or processed the `user.deleted` event — this is a platform-wide NATS delivery-guarantee limitation (core NATS, no JetStream/durable consumers), not something this feature can or should attempt to solve.
- Broadening the `IdentityProvider` interface beyond `delete_user` (e.g. create/update/lookup in the IdP).
- A "deactivate" (reversible, temporary suspension) feature — distinct from offboarding, not built here, but named explicitly so future work doesn't conflate the two.
- "Undo" after execution — offboarding is terminal once executed; there is no restore/reinstate flow. A previously-offboarded person who wants back in goes through onboarding again as a new identity.
- Offboarding for service accounts.
- History/audit table of every schedule/cancel/execute attempt beyond what the fields on `User` capture.

## Further Notes

- Two existing pieces of dead code become load-bearing here: `build_user_deleted_event` (`app/events/user_events.py`) and the unused hard-delete `UserRepository.delete_user` — the latter should be reviewed and either repurposed for the soft-delete execution step or removed, not left as orphaned dead code alongside the new soft-delete path.
- The platform-wide NATS delivery-guarantee gap (core NATS, at-most-once, no JetStream) surfaced during design of this feature but affects every event this platform publishes, not just `user.deleted`. Worth raising separately with whoever owns the `tessera_sdk`/NATS infra as its own initiative — it is called out here only so it isn't mistaken for something this PRD failed to solve.
- Auth0 Management API credentials are a new secret/config surface distinct from the existing OIDC login config (`oidc_domain`, `oidc_issuer`, etc. in `app/config.py`) and will need their own secure provisioning.
