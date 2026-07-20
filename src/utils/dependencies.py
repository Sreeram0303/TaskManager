from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
import jwt
from src.utils.db import get_db
from sqlalchemy.orm import Session
from src.utils.settings import settings
from src.user.models import User
from src.utils.security import decode_token

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials:HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db:Session = Depends(get_db)
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