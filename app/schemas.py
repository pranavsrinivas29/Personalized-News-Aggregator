# app/schemas.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field

# -------- Auth (request/response) --------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

class TokenOut(BaseModel):
    user_id: int
    token: str
