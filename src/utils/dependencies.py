from fastapi import Depends,HTTPException,Cookie,Header, Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
import jwt
import secrets
from arq.connections import ArqRedis
from src.utils.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession 
from src.utils.settings import settings
from src.user.models import User
from src.utils.security import decode_token
from typing import Annotated
bearer_scheme = HTTPBearer()

BearerCredentials = Annotated[HTTPAuthorizationCredentials,Depends(bearer_scheme)]
DbSession = Annotated[AsyncSession,Depends(get_db)]

async def get_current_user(
    credentials:BearerCredentials,
    db:DbSession
):
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401,detail="Invalid Token type")

    # decode_token() accepts any token with sub/exp/type — that includes
    # refresh tokens. Without this check, a refresh token works as a
    # permanent Bearer credential, which defeats the point of splitting
    # short-lived access tokens from long-lived refresh tokens.
    if payload.get("type") != "access":
        raise HTTPException(status_code=401,detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401,detail="Could not validate credentials")

    try:
        user = await db.get(User,int(user_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401,detail="Could not validate credentials")

    if not user:
        raise HTTPException(status_code=401,detail="Could not validate credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=403,detail="User account is inactive")

    return user

CurrentUser = Annotated[User,Depends(get_current_user)]

def verify_csrf(
    csrf_token: Annotated[str | None, Cookie()] = None,
    X_CSRF_Token: Annotated[str | None, Header()] = None,
):
    if not csrf_token or not X_CSRF_Token or not secrets.compare_digest(csrf_token,X_CSRF_Token):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")

async def check_rate_limit(redis_pool: ArqRedis, key: str, ex: int, limit: int) -> None:
    await redis_pool.set(key, 0, ex=ex, nx=True)
    count = await redis_pool.incr(key)
    if count > limit:
        raise HTTPException(status_code=429, detail="Too many attempts, try again later")


def rate_limit_ip(bucket: str, ex: int = 60, limit: int = 5):
    # Factory: called at route-decoration time (e.g. rate_limit_ip("login_attempts")),
    # BEFORE any request exists — so `request` can't be a parameter of THIS function,
    # only of the inner closure FastAPI actually calls per-request via Depends().
    async def _rate_limit_ip(request: Request):
        redis_pool: ArqRedis = request.app.state.redis_pool
        key = f"{bucket}:{request.client.host}"
        await check_rate_limit(redis_pool, key, ex, limit)
    return _rate_limit_ip