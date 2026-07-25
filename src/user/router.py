import secrets
import anyio
from src.user import controller
from sqlalchemy.orm import Session
from src.utils.db import get_db
from src.utils.dependencies import verify_csrf
from src.utils.settings import settings
from typing import Annotated
from fastapi import APIRouter, Depends,status, Request,Response, Cookie,Header,HTTPException
from src.user.dtos import UserSchema, UserResponseSchema, LoginSchema,TokenSchema

router = APIRouter(prefix="/users",tags=["Users"])

@router.post("/register",response_model=UserResponseSchema,responses={409: {"description": "Username or email already registered"}},status_code=status.HTTP_201_CREATED)
def register(body:UserSchema,request:Request,db:Session = Depends(get_db)):
    pool = request.app.state.redis_pool
    new_user = controller.register(body,db)
    anyio.from_thread.run(pool.enqueue_job,"send_welcome_email",body.email)
    return new_user

@router.post("/login",status_code=status.HTTP_200_OK,response_model=TokenSchema,responses={401:{"description":"Invalid Credentials"}})
def login(body:LoginSchema,response:Response,db:Session = Depends(get_db)):
    token_payload = controller.login(body,db)
    response.set_cookie(value=token_payload["refresh_token"],
                        key="refresh_token",
                        httponly=True,
                        secure=False,
                        samesite="lax",
                        path = "/users",
                        max_age=settings.JWT_REFRESH_EXPIRE_DAYS*24*60*60
                        )
    response.set_cookie(value= secrets.token_urlsafe(32),
                        key="csrf_token",
                        httponly=False,
                        secure=False,
                        samesite="lax",
                        path = "/users",
                        max_age=settings.JWT_REFRESH_EXPIRE_DAYS*24*60*60
                        )
    return token_payload


@router.post(
    "/refresh",
    dependencies=[Depends(verify_csrf)],
    response_model=TokenSchema,
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Invalid or expired refresh token"},
               403 : {"description" : "CSRF Mismatch"}}
)
def refresh(response:Response,db:Annotated[Session,Depends(get_db)],
            refresh_token : Annotated[str|None,Cookie()] = None):
    if(not refresh_token ):
        raise HTTPException(status_code=401)
    token_payload = controller.refresh_access_token(refresh_token, db)
    response.set_cookie(value=token_payload["refresh_token"],
                        key="refresh_token",
                        httponly=True,
                        secure=False,
                        samesite="lax",
                        path = "/users",
                        max_age=settings.JWT_REFRESH_EXPIRE_DAYS*24*60*60
    )
    response.set_cookie(value= secrets.token_urlsafe(32),
                        key="csrf_token",
                        httponly=False,
                        secure=False,
                        samesite="lax",
                        path = "/users",
                        max_age=settings.JWT_REFRESH_EXPIRE_DAYS*24*60*60
                        )
    return token_payload


@router.post("/logout", status_code=status.HTTP_200_OK,dependencies=[Depends(verify_csrf)])
def logout(response:Response,refresh_token:Annotated[str|None,Cookie()]=None, db: Session = Depends(get_db)):
    if(not refresh_token):
        raise HTTPException(status_code=401)
    payload = controller.logout(refresh_token, db)
    response.delete_cookie(key="refresh_token",path="/users")
    return payload