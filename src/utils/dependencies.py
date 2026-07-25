from fastapi import Depends,HTTPException,Cookie,Header
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
import jwt
from src.utils.db import get_db
from sqlalchemy.orm import Session
from src.utils.settings import settings
from src.user.models import User
from src.utils.security import decode_token
from typing import Annotated
import secrets
bearer_scheme = HTTPBearer()

BearerCredentials = Annotated[HTTPAuthorizationCredentials,Depends(bearer_scheme)]
DbSession = Annotated[Session,Depends(get_db)]

def get_current_user(
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
        user = db.get(User,int(user_id))
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
