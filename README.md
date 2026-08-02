# TaskManager

A task management API built as a deep dive into production backend engineering — not a CRUD tutorial project. Every feature exists to explore a real system-design problem: token theft, race conditions, cache invalidation, authorization boundaries, real-time fan-out across multiple processes. Built incrementally, with a real `pytest` suite (24 tests) that has already caught two live bugs before they shipped — an authentication bypass and a cascade-delete crash.

## Tech stack

- **FastAPI** (fully async) + **SQLAlchemy 2.0** (async, `asyncpg`)
- **PostgreSQL** — primary datastore
- **Redis** — three distinct roles in one instance: `arq` job queue, cache-aside layer, and Pub/Sub for real-time sync
- **Alembic** — schema migrations
- **pytest** — automated test suite (24 tests), isolated test database + isolated Redis logical DB
- **Docker Compose** — the full stack (API, worker, Postgres, Redis), not just infra dependencies

## What's actually built

**Authentication & session security**
- Argon2id password hashing (not bcrypt — memory-hard, GPU-resistant)
- JWT access tokens (short-lived) + refresh tokens (long-lived), fully separated by a `type` claim so a leaked refresh token can't be used as a permanent access credential
- **Refresh token rotation with reuse detection** — a rotated-away token being replayed triggers a full session wipe for that user, treating it as a signal of compromise
- Refresh token delivered via an **httpOnly cookie** (XSS-resistant); access token stays Bearer-header (immune to CSRF by construction, since browsers don't auto-attach custom headers cross-site)
- **CSRF protection** (double-submit cookie pattern) on the two routes that *do* rely on a cookie — verified with `secrets.compare_digest`, not `==`
- **Rate limiting** on `/login` and `/register` — both IP-based (a parameterized dependency factory, one implementation, separate counters per route) and email-based, atomic `SET...NX EX` + `INCR` to avoid a race between checking and incrementing

**Authorization (RBAC)**
- Real `Role`/`Permission` schema (many-to-many both directions), not a single `is_admin` flag — but populated with exactly one real permission today (`view_admin_dashboard`), not several pre-invented ones with nothing to enforce yet
- Every user gets a baseline `member` role automatically at registration; `admin` is never self-assignable through the API on purpose
- `GET /admin/dashboard` (total users, total tasks, cache hit/miss stats) — gated behind the permission system, not a hardcoded role check

**Caching & performance**
- Cache-aside layer on `GET /tasks` with automatic invalidation on every write, and Redis-outage resilience (a cache failure degrades to "always hit the DB," never fails the request)
- Pagination (`page`/`page_size`, `has_next` via a fetch-one-extra trick — no separate `COUNT` query) plus search/filter (`is_completed`, `search`) applied in-memory over the cached full list, deliberately not one cache key per page — a personal task list is small enough that this stays simple without the multi-key invalidation problem that design would otherwise create
- Cache hit/miss counters surfaced in the admin dashboard, so "is the cache actually helping" has a real answer instead of an assumption

**Real-time multi-device sync**
- Task mutations broadcast live to every open connection for that user via **Server-Sent Events + Redis Pub/Sub** — complete a task on your phone, an open laptop tab updates with no refresh
- Short-lived, single-use **ticket-based auth** for the SSE handshake (`EventSource` can't set an `Authorization` header) — the real access token never touches a URL or a log line
- Verified live across two real browser tabs via a dedicated demo page (`frontend_demo/realtime_demo.html`), not just reasoned about

**Data layer**
- Fully async SQLAlchemy — `create_async_engine`, `async_sessionmaker`, every route and controller awaiting real I/O instead of blocking a thread
- A custom `UTCDateTime` type that refuses to store an ambiguous (naive) datetime at write time, rather than allowing a silent timezone bug into the database
- Alembic-versioned schema; cascading deletes enforced at the DB level (`ondelete="CASCADE"`) *and* correctly disarmed on the ORM side (`passive_deletes=True`) — verified live that skipping the latter actually crashes a user delete, not just wastes a query
- Scheduled cleanup: an `arq` cron job purges expired/revoked refresh tokens daily via a bulk `DELETE`, not a per-row load-then-delete

**Infrastructure**
- Request-ID + duration logging middleware, using `contextvars` so the ID is readable from anywhere in the call stack without threading it through every function signature
- Security headers on every response (`X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security` once actually deployed behind HTTPS) — CSP deliberately skipped, since this app only ever returns JSON and has no script-execution surface for a content policy to restrict
- Environment-aware cookie security (`COOKIE_SECURE`) — `False` for local HTTP dev, flips to `True` behind real HTTPS with no other code change; TLS itself terminates at a reverse proxy/load balancer in front of the app, never inside the FastAPI process
- CORS configured and verified against a real cross-origin demo page, not just assumed correct
- **Async background job queue** (`arq` + Redis) for the welcome email — deliberately not `BackgroundTasks`, because an in-process background task is lost on server restart; a queued job survives it (proven live: a job sat in Redis for ~9 minutes waiting for a worker, and was still processed correctly once one started)
- Fully containerized: API, worker, Postgres, and Redis all run via one `docker compose up`, sharing a single built image between the API and worker (same code, different startup command)

**Testing**
- 24 tests covering registration, login, refresh rotation + reuse detection, CSRF enforcement, task CRUD, pagination, search/filter, cache observability, RBAC (member vs admin), cross-user ownership isolation, cross-user activity isolation, security headers, and cascade-delete behavior
- Runs against an isolated `taskmanager_test` Postgres database and an isolated Redis logical DB (index 15) — the real database engine, not a SQLite stand-in, so nothing is ever tested against behavior Postgres wouldn't actually exhibit

## A few engineering decisions worth knowing about

- **Why not SQLite for tests, or ever?** Early in the project, a timestamp bug was completely invisible on SQLite and only surfaced once the app moved to Postgres — SQLite doesn't meaningfully enforce the same column-type guarantees. Tests run against real Postgres specifically to avoid re-introducing that gap.
- **Why `arq` over `celery`?** Async-native, Redis-only, no extra infrastructure concepts beyond what the app already uses.
- **Why SSE over WebSockets for real-time sync?** The actual traffic here is one-directional — task mutations always go through normal REST, the live channel only ever pushes "something changed." SSE is the better-fitting tool for that: plain HTTP, native browser reconnect, no protocol upgrade. WebSockets were the more familiar name, not the better fit for this specific problem.
- **Why one real permission instead of a handful of plausible-sounding ones?** The RBAC schema (roles, permissions, both many-to-many) is fully general — adding a second role or permission later needs zero schema changes, just new rows. Populating it with permissions that have no second enforcement point yet would just be unused ceremony.
- **A real bug the test suite caught:** during the async conversion, a threadpool-wrapped password verification call was missing its `await`. Since an un-awaited coroutine is always truthy in a boolean check, the login route's password check silently stopped doing anything — any password would have authenticated as any existing user. `test_login_wrong_password_returns_401` failed immediately, and the bug was fixed before it ever reached a deployed branch.
- **A second real bug, caught by deliberately testing the "obviously fine" case:** removing `passive_deletes=True` and rerunning the cascade-delete test wasn't just documentation — it proved deleting a user would otherwise crash outright (SQLAlchemy tries to null out each child's foreign key before the parent delete; Postgres rejects it since those columns aren't nullable), not merely run an extra, wasted query.

## Project structure

```
src/
  task/         # task CRUD — models, DTOs, controller, router
  user/         # auth — register/login/refresh/logout/me, models, DTOs
  authz/        # RBAC — Role/Permission models, association tables
  admin/        # admin-only dashboard (users, tasks, cache stats)
  activity/     # activity feed read endpoint
  realtime/     # SSE ticket auth + event stream (Redis Pub/Sub)
  utils/        # db, settings, security (hashing/JWT), dependencies,
                # middleware, security headers, arq worker config,
                # activity logging
migrations/     # Alembic revisions
tests/          # pytest suite
frontend_demo/  # two deliberately minimal HTML pages proving CORS and
                # real-time sync against a real browser, not just TestClient
conftest.py     # test DB + Redis isolation setup
docker-compose.yml   # API, worker, Postgres, Redis — the full stack
```

## Running it locally

**1. Set up your environment:**
```
cp .env.example .env
# fill in real values — see .env.example for what's needed
```

**2. Start the full stack** (Postgres, Redis, API, worker):
```
docker compose up -d --build
```

**3. Run migrations** (schema is Alembic-managed, not auto-created):
```
pip install -r requirements.txt
alembic upgrade head
```

**4. Run the tests:**
```
pytest -v
```

API docs are auto-generated at `http://localhost:8000/docs` once the stack is running. The real-time sync demo (`frontend_demo/realtime_demo.html`) needs a static server on `http://localhost:5500` to match the app's configured CORS origin.
