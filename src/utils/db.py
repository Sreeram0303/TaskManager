from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import DateTime, TypeDecorator
from src.utils.settings import settings

# connect_args={"check_same_thread": False} is a SQLite-only workaround
# (SQLite connections are single-thread by default; FastAPI's dependency
# may use a connection from a different thread than it was created on).
# Postgres/MySQL drivers don't accept this kwarg — gate it on the URL scheme
# so switching DB_CONNECTION doesn't crash create_engine.
_connect_args = {"check_same_thread": False} if settings.DB_CONNECTION.startswith("sqlite") else {}
engine = create_engine(url=settings.DB_CONNECTION, connect_args=_connect_args)  # connection to DB
LocalSession = sessionmaker(bind = engine) # session creatoor. session - task , unit work

@event.listens_for(engine, "connect")
def enable_sqlite_fks(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class Base(DeclarativeBase):
    pass # registery for tables


class UTCDateTime(TypeDecorator):
    """DateTime column that is always timezone-aware UTC on both ends.

    SQLite has no native timezone-aware datetime type: it silently drops
    tzinfo on read even when a tz-aware value was written (confirmed live —
    a stored datetime.now(timezone.utc) comes back naive). That makes a
    later `< utc_now()` comparison raise "can't compare offset-naive and
    offset-aware datetimes". This type re-attaches UTC on load, and refuses
    naive input on write so a caller can't silently store an ambiguous time.
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def get_db():
    session = LocalSession()
    try:
        yield session
    except Exception:
        # Unit-of-work rule: if anything raised mid-transaction, the
        # session must not be left holding a half-done transaction —
        # roll it back before closing, else the next use of this
        # connection can inherit stale/uncommitted state.
        session.rollback()
        raise
    finally:
        session.close()
