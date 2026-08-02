from src.user.dtos import UserSchema,LoginSchema
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy import select,update
from src.user.models import User,RefreshToken
from src.authz.models import Role
from fastapi import HTTPException
from src.utils.security import hash_password, verify_password, create_access_token,create_refresh_token, decode_token
from sqlalchemy.exc import IntegrityError
from src.utils.helpers import utc_now
from fastapi.concurrency import run_in_threadpool
async def register(body:UserSchema,db:AsyncSession):
    # userame checks
    username = (await db.scalars(select(User).where(User.username == body.username))).first()
    if username:
        raise HTTPException(status_code=409,detail="Username already taken")
    # email checks
    email = (await db.scalars(select(User).where(User.email == body.email))).first()
    if email:
        raise HTTPException(status_code=409,detail="Email already registered")
    hashed_password = await run_in_threadpool(hash_password,body.password)
    
    new_user = User(
        email = body.email,
        username = body.username,
        hashed_password = hashed_password
    )
    # Every user gets the baseline "member" role automatically — "admin"
    # is never self-assignable, that has to be a deliberate, separate
    # action (a manual DB change today), not something registration grants.
    member_role = (await db.scalars(select(Role).where(Role.name == "member"))).first()
    new_user.roles.append(member_role)
    db.add(new_user)
    try :
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409,detail="Username or email already registered")
    await db.refresh(new_user)
    return new_user


async def issue_tokens(user:User,db:AsyncSession) -> dict:
    access_token = create_access_token(user.id)
    refresh_token,jti,expires_at = create_refresh_token(user.id)
    
    db.add(RefreshToken(user_id=user.id,jti=jti,expires_at=expires_at))
    await db.commit()
    
    return {"access_token": access_token,"refresh_token":refresh_token,"token_type":"bearer"}
    

async def login(body:LoginSchema,db:AsyncSession):
    user = (await db.scalars(select(User).where(User.email == body.email))).first()
    
    if not user or not await run_in_threadpool(verify_password,body.password,user.hashed_password):
        raise HTTPException(status_code=401,detail="Invalid Credentials")
    return await issue_tokens(user,db)

async def refresh_access_token(refresh_token: str, db: AsyncSession):
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    token_row = (await db.scalars(select(RefreshToken).where(RefreshToken.jti == jti))).first()

    if not token_row:
        raise HTTPException(status_code=401, detail="Refresh token not recognized")

    if token_row.revoked:
        # Reuse of an already-rotated token — treat as compromise, kill all sessions
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id)
            .values(revoked=True)
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected — all sessions revoked")

    if token_row.expires_at < utc_now():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = await db.get(User, token_row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    token_row.revoked = True  # rotate: this one is now spent
    await db.commit()

    return await issue_tokens(user, db)


async def logout(refresh_token: str, db: AsyncSession):
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    jti = payload.get("jti")
    await db.execute(update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True))
    await db.commit()
    return {"detail": "Logged out successfully"}