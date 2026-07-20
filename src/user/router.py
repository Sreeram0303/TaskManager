from fastapi import APIRouter, Depends,status
from src.user import controller
from src.user.dtos import UserSchema, UserResponseSchema, LoginSchema,TokenSchema,RefreshSchema
from sqlalchemy.orm import Session
from src.utils.db import get_db
from src.user.models import User
from src.utils.dependencies import get_current_user
router = APIRouter(prefix="/users",tags=["Users"])

@router.post("/register",response_model=UserResponseSchema,responses={409: {"description": "Username or email already registered"}},status_code=status.HTTP_201_CREATED)
def register(body:UserSchema,db:Session = Depends(get_db)):
    return controller.register(body,db)


@router.post("/login",status_code=status.HTTP_200_OK,response_model=TokenSchema,responses={401:{"description":"Invalid Credentials"}})
def login(body:LoginSchema,db:Session = Depends(get_db)):
    return controller.login(body,db)


@router.post(
    "/refresh",
    response_model=TokenSchema,
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Invalid or expired refresh token"}}
)
def refresh(body: RefreshSchema, db: Session = Depends(get_db)):
    return controller.refresh_access_token(body.refresh_token, db)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(body: RefreshSchema, db: Session = Depends(get_db)):
    return controller.logout(body.refresh_token, db)