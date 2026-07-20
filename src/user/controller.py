from src.user.dtos import UserSchema,LoginSchema
from sqlalchemy.orm import Session
from sqlalchemy import select,update
from src.user.models import User,RefreshToken
from fastapi import HTTPException
from src.utils.security import hash_password, verify_password, create_access_token,create_refresh_token, decode_token
from sqlalchemy.exc import IntegrityError
from src.utils.helpers import utc_now
def register(body:UserSchema,db:Session):
    # userame checks
    username = db.scalars(select(User).where(User.username == body.username)).first()
    if username:
        raise HTTPException(status_code=409,detail="Username already taken")
    # email checks
    email = db.scalars(select(User).where(User.email == body.email)).first()
    if email:
        raise HTTPException(status_code=409,detail="Email already registered")
    hashed_password = hash_password(body.password)
    
    new_user = User(
        email = body.email,
        username = body.username,
        hashed_password = hashed_password
    )
    db.add(new_user)
    try :
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail="Username or email already registered")
    db.refresh(new_user)
    return new_user


def issue_tokens(user:User,db:Session) -> dict:
    access_token = create_access_token(user.id)
    refresh_token,jti,expires_at = create_refresh_token(user.id)
    
    db.add(RefreshToken(user_id=user.id,jti=jti,expires_at=expires_at))
    db.commit()
    
    return {"access_token": access_token,"refresh_token":refresh_token,"token_type":"bearer"}
    

def login(body:LoginSchema,db:Session):
    user = db.scalars(select(User).where(User.email == body.email)).first()
    
    if not user or not verify_password(body.password,user.hashed_password):
        raise HTTPException(status_code=401,detail="Invalid Credentials")
    return issue_tokens(user,db)

def refresh_access_token(refresh_token: str, db: Session):
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    token_row = db.scalars(select(RefreshToken).where(RefreshToken.jti == jti)).first()

    if not token_row:
        raise HTTPException(status_code=401, detail="Refresh token not recognized")

    if token_row.revoked:
        # Reuse of an already-rotated token — treat as compromise, kill all sessions
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id)
            .values(revoked=True)
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected — all sessions revoked")

    if token_row.expires_at < utc_now():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.get(User, token_row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    token_row.revoked = True  # rotate: this one is now spent
    db.commit()

    return issue_tokens(user, db)


def logout(refresh_token: str, db: Session):
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    jti = payload.get("jti")
    db.execute(update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True))
    db.commit()
    return {"detail": "Logged out successfully"}