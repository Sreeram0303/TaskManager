from pydantic import BaseModel


class CacheStatsSchema(BaseModel):
    hits: int
    misses: int
    hit_rate: float | None


class AdminDashboardSchema(BaseModel):
    total_users: int
    total_tasks: int
    cache: CacheStatsSchema
