from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta
from src.utils.settings import settings
from src.utils.helpers import utc_now
import uuid

# ------ Password Hashing ------ #
password_hash = PasswordHash.recommended()

def hash_password(password:str)->str:
    return password_hash.hash(password)

def  verify_password(password:str,hashed_password:str) -> bool:
    return password_hash.verify(password,hashed_password)

# ------ JWT ------ #

def create_access_token(user_id:int)->str:
    payload = {
        "sub" : str(user_id),
        "exp" : utc_now() +
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
        "type": "access"
    }

    return jwt.encode(payload=payload,key=settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    expire = utc_now() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh", "jti": jti}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire
    
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "type"]}
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")