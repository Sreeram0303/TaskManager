from datetime import datetime
from sqlalchemy import String,ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.utils.db import Base, UTCDateTime
from src.utils.helpers import utc_now


class Task(Base):
    __tablename__ = "user_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
    is_completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    owner : Mapped["User"] = relationship(back_populates="tasks")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(50))       # "task_created", "task_completed"...
    detail: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
