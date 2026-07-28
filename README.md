# TaskManager

A task management API built as a deep dive into production backend engineering — not a CRUD tutorial project. Every feature exists to explore a real system-design problem: token theft, race conditions, request durability, async I/O correctness. Built incrementally, with a real `pytest` suite that has already caught a live authentication bug before it shipped.

## Tech stack

- **FastAPI** (fully async) + **SQLAlchemy 2.0** (async, `asyncpg`)
- **PostgreSQL** — primary datastore, running in Docker
- **Redis** + **arq** — background job queue (async-native, not Celery)
- **Alembic** — schema migrations
- **pytest** — automated test suite, isolated test database
- **Docker Compose** — Postgres + Redis, dedicated to this project

## What's actually built

**Authentication & session security**
- Argon2id password hashing (not bcrypt — memory-hard, GPU-resistant)
- JWT access tokens (short-lived) + refresh tokens (long-lived), fully separated by a `type` claim so a leaked refresh token can't be used as a permanent access credential
- **Refresh token rotation with reuse detection** — a rotated-away token being replayed triggers a full session wipe for that user, treating it as a signal of compromise
- Refresh token delivered via an **httpOnly cookie** (XSS-resistant); access token stays Bearer-header (immune to CSRF by construction, since browsers don't auto-attach custom headers cross-site)
- **CSRF protection** (double-submit cookie pattern) on the two routes that *do* rely on a cookie — verified with `secrets.compare_digest`, not `==`

**Data layer**
- Fully async SQLAlchemy — `create_async_engine`, `async_sessionmaker`, every route and controller awaiting real I/O instead of blocking a thread
- A custom `UTCDateTime` type that refuses to store an ambiguous (naive) datetime at write time, rather than allowing a silent timezone bug into the database
- Alembic-versioned schema, cascading deletes modeled at the DB level

**Infrastructure**
- Request-ID + duration logging middleware, using `contextvars` so the ID is readable from anywhere in the call stack without threading it through every function signature
- CORS configured and verified against a real cross-origin demo page, not just assumed correct
- **Async background job queue** (`arq` + Redis) for the welcome email — deliberately not `BackgroundTasks`, because an in-process background task is lost on server restart; a queued job survives it (proven live: a job sat in Redis for ~9 minutes waiting for a worker, and was still processed correctly once one started)

**Testing**
- 12 tests covering registration, login, refresh rotation + reuse detection, CSRF enforcement, task CRUD, and cross-user ownership isolation
- Runs against an isolated `taskmanager_test` Postgres database — the real database engine, not a SQLite stand-in, to avoid divergence between what's tested and what's deployed

## A few engineering decisions worth knowing about

- **Why not SQLite for tests, or ever?** Early in the project, a timestamp bug was completely invisible on SQLite and only surfaced once the app moved to Postgres — SQLite doesn't meaningfully enforce the same column-type guarantees. Tests run against real Postgres specifically to avoid re-introducing that gap.
- **Why `arq` over `celery`?** Async-native, Redis-only, no extra infrastructure concepts beyond what the app already uses.
- **Why does `register` bridge into Redis with a direct `await` instead of a thread bridge?** It didn't always — an earlier version used `anyio.from_thread.run()` because the route was still synchronous. Once the whole app was converted to async, that bridge became not just unnecessary but actively broken (confirmed live: it raised `NoEventLoopError`, since the route no longer runs in a worker thread at all). Removed in favor of a direct `await`.
- **A real bug the test suite caught:** during the async conversion, a threadpool-wrapped password verification call was missing its `await`. Since an un-awaited coroutine is always truthy in a boolean check, the login route's password check silently stopped doing anything — any password would have authenticated as any existing user. The test suite's `test_login_wrong_password_returns_401` failed immediately, and the bug was fixed before it ever reached a deployed branch.

## Project structure

```
src/
  task/         # task CRUD — models, DTOs, controller, router
  user/         # auth — register/login/refresh/logout, models, DTOs
  utils/        # db, settings, security (hashing/JWT), dependencies,
                # middleware, arq worker config, activity logging
migrations/     # Alembic revisions
tests/          # pytest suite
conftest.py     # test DB isolation setup
docker-compose.yml   # Postgres + Redis
```

## Running it locally

**1. Start Postgres and Redis:**
```
docker compose up -d
```

**2. Set up your environment:**
```
cp .env.example .env
# fill in real values — see .env.example for what's needed
```

**3. Install dependencies and run migrations:**
```
pip install -r requirements.txt
alembic upgrade head
```

**4. Run the API:**
```
uvicorn main:app --reload
```

**5. Run the background job worker** (separate terminal — this is a genuine second process, not optional):
```
arq src.utils.arq_functions.WorkerSettings
```

**6. Run the tests:**
```
pytest -v
```

API docs are auto-generated at `http://localhost:8000/docs` once the server is running.
