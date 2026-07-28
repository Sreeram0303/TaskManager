import os
from dotenv import load_dotenv

# Load .env FIRST, before any app import — we need POSTGRES_USER/PASSWORD
# from it to build the test DB URL, without hardcoding a password here
# (this file gets committed; .env doesn't).
load_dotenv()

_user = os.environ["POSTGRES_USER"]
_password = os.environ["POSTGRES_PASSWORD"]

# Override DB_CONNECTION BEFORE main/settings/db get imported anywhere.
# settings = Settings() and engine = create_engine(...) both run at import
# time — once that happens, it's too late to redirect them by patching
# settings afterward. This line has to come before the import below.
os.environ["DB_CONNECTION"] = f"postgresql://{_user}:{_password}@localhost:5432/taskmanager_test"

import pytest
from fastapi.testclient import TestClient
from main import app
from src.utils.db import engine


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
        # engine is a module-level singleton, created once at import time and
        # bound to whichever event loop first used it. TestClient spins up a
        # FRESH event loop per test (anyio.from_thread.start_blocking_portal
        # in __enter__) — so without disposing here, the next test's new loop
        # inherits connections tied to THIS test's loop, which is about to
        # die the moment this `with` block exits. Same root cause as the arq
        # pool's "Event loop is closed" bug, different symptom.
        # Must run on c's own portal — its loop is still alive here, right
        # before the `with` block's __exit__ tears it down.
        c.portal.call(engine.dispose)
