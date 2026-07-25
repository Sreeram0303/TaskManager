from datetime import  timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import DateTime, TypeDecorator
from src.utils.settings import settings


engine = create_engine(url=settings.DB_CONNECTION)  # connection to DB
LocalSession = sessionmaker(bind = engine) # session creatoor. session - task , unit work

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
