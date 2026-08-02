from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.user.models import User
from src.task.models import Task
from arq.connections import ArqRedis


async def get_dashboard(db: AsyncSession, redis_pool: ArqRedis):
    user_count = await db.scalar(select(func.count()).select_from(User))
    task_count = await db.scalar(select(func.count()).select_from(Task))

    hits = int(await redis_pool.get("cache_stats:hits") or 0)
    misses = int(await redis_pool.get("cache_stats:misses") or 0)
    total = hits + misses

    return {
        "total_users": user_count,
        "total_tasks": task_count,
        "cache": {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 4) if total else None,
        },
    }
