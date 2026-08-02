from fastapi import APIRouter, Request
from arq.connections import ArqRedis
from src.utils.dependencies import CurrentUser

# Least-exposure default: no specific reason this needs to be reachable
# by someone who hasn't logged in, so — same as every other non-public
# route in this app — it sits behind CurrentUser. "Not that sensitive"
# isn't a strong enough reason to leave a route open; "no reason to
# protect it" was the wrong question to be asking in the first place.
router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/cache")
async def cache_stats(request: Request, current_user: CurrentUser):
    redis_pool: ArqRedis = request.app.state.redis_pool
    hits = int(await redis_pool.get("cache_stats:hits") or 0)
    misses = int(await redis_pool.get("cache_stats:misses") or 0)
    total = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / total, 4) if total else None,
    }
