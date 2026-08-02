from fastapi import APIRouter,Request,Depends,HTTPException
from fastapi.responses import StreamingResponse
from src.utils.dependencies import CurrentUser
from arq.connections import ArqRedis
import secrets
router = APIRouter(prefix="/realtime",tags=["realtime"])

@router.post("/")
async def func(request : Request,current_user : CurrentUser):
    redis_pool : ArqRedis = request.app.state.redis_pool
    ticket = secrets.token_urlsafe(32)
    key = f"sse_ticket:{ticket}"
    await redis_pool.set(key,current_user.id,ex=30,nx=True)
    return {"ticket" : ticket }


async def _event_stream(redis_pool: ArqRedis, user_id: int):
    # A dedicated subscription — separate from the shared pool's normal
    # request/response usage, and it stays open for as long as this
    # generator is alive (i.e. for the whole SSE connection's lifetime).
    pubsub = redis_pool.pubsub()
    channel = f"user:{user_id}:events"
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            # listen()'s first item is always the subscribe confirmation
            # itself (type="subscribe"), not a published event — only
            # type="message" entries are real PUBLISH payloads.
            if message["type"] != "message":
                continue
            # message["data"] is raw bytes (this connection isn't set up
            # with decode_responses=True) — decode explicitly, otherwise
            # an f-string just str()'s the bytes object into its repr,
            # literally "b'...'", which isn't valid JSON on the wire.
            payload = message["data"].decode()
            # SSE wire format: "data: <payload>\n\n" — the blank line
            # (two trailing \n) is what tells the browser one event ended.
            yield f"data: {payload}\n\n"
    finally:
        # Runs once this generator is closed — either the client
        # disconnected (Starlette lets the abandoned generator get
        # GC'd, which raises GeneratorExit here) or the loop above
        # exits some other way. Without this, every disconnect would
        # leak one live subscription on the Redis side.
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


@router.get("/events")
async def stream_events(request: Request, ticket: str):
    redis_pool: ArqRedis = request.app.state.redis_pool

    # Redeem: GETDEL reads and deletes in one atomic step, so the same
    # ticket can never be redeemed twice even under concurrent requests.
    user_id = await redis_pool.getdel(f"sse_ticket:{ticket}")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired ticket")

    return StreamingResponse(
        _event_stream(redis_pool, int(user_id)),
        media_type="text/event-stream",
    )