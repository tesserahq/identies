# Development

## Setup

Follow [Quick Setup](quick_setup.md). Then:

```bash
poetry run dev                       # run with reload
ENV=test poetry run pytest tests/    # run the tests
poetry run black app tests           # format
poetry run alembic upgrade head      # migrations
```

## Running the tests

The tests need a PostgreSQL server and a database named **`identies_test`**. Create it once:

```bash
docker run -d --name identies-pg -e POSTGRES_PASSWORD=postgres -p 127.0.0.1:5432:5432 postgres:17
docker exec identies-pg psql -U postgres -c "CREATE DATABASE identies_test"
```

`ENV=test` makes the app use `TEST_DATABASE_URL` (default
`postgresql://postgres:postgres@localhost:5432/identies_test`). The test configuration file
creates a database named `vaulta_test` if it is missing, which appears to be a leftover from another
service; the database the tests actually use is `identies_test`, and it must exist.

The test session creates all tables from the models, so it does not run migrations.

### Test conventions

- Test **behaviour** through public interfaces (HTTP responses, persisted state, published events), not private helpers.
- The shared `db` fixture wraps each test in **one transaction**. A `db.rollback()` inside the code under test rolls back the fixture's own data. If a code path only needs to *release a lock*, commit a no-op transaction instead of rolling back.
- Router tests that check **who may call what** must use the real authentication middleware, not the test mock. `tests/app/routers/test_agent_router.py` and `test_agent_credentials.py` show how: patch `TokenHandler.verify`, or mint real tokens with generated RSA keys.
- Concurrency claims need a **real** concurrency test with separate sessions and a way to prove it fails without the protection. Widen the critical section artificially and open connections before the barrier, or the threads never overlap.
- Mock the NATS publisher by passing a `MagicMock` as `nats_publisher` to a command.

## Code layout

| Layer | Where | Rule |
|---|---|---|
| Routers | `app/routers/` | Thin: validate, authorize, call a command, shape the response |
| Commands | `app/commands/<domain>/` | One class per operation with a single public `execute()`; publishes events |
| Repositories | `app/repositories/` | Data access; **every user lookup must exclude soft-deleted rows** |
| Models | `app/models/` | SQLAlchemy models; `kind` is required on users |
| Events | `app/events/` | Builders only; commands publish them |
| Schemas | `app/schemas/` | Pydantic request/response models |

## Checklists

### Adding a route

1. Put it in the right router and give it an `operation_id`.
2. Decide its [path class](authentication.md#path-classes). A privileged route belongs under a service-only prefix; add the prefix to `M2M_AUTH_PATHS`.
3. Add a Custos permission (`rbac[...]`) unless it has its own documented rule.
4. **Update the API reference**: `poetry run python -m tests.docs.route_inventory --write`, and add prose if it needs any.
5. If it can be reached by a principal it should not be, add a test through the real middleware.

### Adding a setting

Add it to `Settings`, then to [Configuration](configuration.md). A test fails if you forget.

### Adding an event

Add the builder and constant, publish it from the command, then list it in [Events](events.md). A
test fails if you forget. Never put a secret in an event.

### Adding a migration

Backfill in the migration, add the constraint afterwards, verify upgrade/downgrade/upgrade on real
data, and describe rollout and rollback caveats in [Operations](operations.md#migration-notes).

## Keeping the docs honest

Some documentation is verified by tests in `tests/docs/`:

| Check | What it guards |
|---|---|
| The route table in the API reference equals the routes and their permissions in the code | A route, path class or permission changes without the doc |
| Every setting appears in Configuration, and every variable Configuration lists exists | A setting is added, renamed or removed without the doc |
| Every event type appears in Events | An event is added without the doc |
| Every page is in the site navigation, and every relative link resolves | Broken or orphaned pages |

If one fails, the message says how to fix it.

## Design records

Why the system is shaped this way — and what was tried and rejected — is in
[Design Decisions](decisions.md). Add an entry there when you make a decision that someone might
later want to reverse.
