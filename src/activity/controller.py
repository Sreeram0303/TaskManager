from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.task.models import ActivityLog
from src.activity.dtos import ActivityLogResponseSchema


async def get_activity(db: AsyncSession, user_id: int, page: int, page_size: int):
    start = (page - 1) * page_size
    rows = (
        await db.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.created_at.desc())
            .offset(start)
            .limit(page_size + 1)
        )
    ).all()

    has_next = len(rows) > page_size
    rows = rows[:page_size]

    items = [ActivityLogResponseSchema.model_validate(row) for row in rows]
    return {"items": items, "has_next": has_next}
