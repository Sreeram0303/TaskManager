from pydantic import BaseModel,EmailStr,Field
from datetime import datetime

# username max_length mirrors models.py User.username = String(100).
# password bounds are an edge-validation habit, not a hashing requirement —
# argon2id in security.py would happily hash "" or a 10000-char string,
# which is exactly why the DB/hash layer must not be the first line of defense.
class UserSchema(BaseModel):
    username : str = Field(min_length=3,max_length=100)
    email : EmailStr
    password : str = Field(min_length=8,max_length=128)

class UserResponseSchema(BaseModel):
    id : int
    username : str
    email : str
    created_at : datetime
    
    
class LoginSchema(BaseModel):
    email : EmailStr
    password : str
    
    
class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type:str="bearer"
    
class RefreshSchema(BaseModel):
    refresh_token: str