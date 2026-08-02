from src.utils.db import Base, UTCDateTime
from sqlalchemy.orm import Mapped,mapped_column, relationship
from sqlalchemy import String,Integer, ForeignKey
from datetime import datetime
from src.utils.helpers import utc_now


class User(Base):
    __tablename__ = 'users'

    id : Mapped[int] = mapped_column(primary_key=True)
    username : Mapped[str] = mapped_column(String(100),unique=True)
    email : Mapped[str] = mapped_column(String(255),unique=True)
    hashed_password : Mapped[str] = mapped_column(String(255))
    is_active : Mapped[bool] = mapped_column(default=True)
    created_at : Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    # passive_deletes=True on all three: ondelete="CASCADE" is already set
    # at the DB level on each child's FK (or on user_roles, for roles) — so
    # deleting a User should just issue that one DELETE and trust Postgres
    # to clean up tasks/refresh_tokens/user_roles, not have SQLAlchemy try
    # to SELECT+DELETE (or NULL-out) each collection itself first.
    # passive_deletes=True on all three: ondelete="CASCADE" is already set
    # at the DB level on each child's FK (or on user_roles, for roles) — so
    # deleting a User should just issue that one DELETE and trust Postgres
    # to clean up tasks/refresh_tokens/user_roles, not have SQLAlchemy try
    # to SELECT+DELETE (or NULL-out) each collection itself first.
    #
    # Verified live this actually matters, not just an optimization: WITHOUT
    # passive_deletes=True, deleting a user crashes outright — SQLAlchemy
    # tries "UPDATE user_tasks SET user_id=NULL ..." before the delete,
    # which Postgres rejects since user_id isn't nullable (NotNullViolationError).
    tasks: Mapped[list["Task"]] = relationship(back_populates="owner", passive_deletes=True)
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", passive_deletes=True)
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users", passive_deletes=True)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    