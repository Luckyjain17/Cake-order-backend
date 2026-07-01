from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AdminUserBase(BaseModel):
    username: str
    email: str


class AdminUserCreate(AdminUserBase):
    password: str


class AdminUserOut(AdminUserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminUserOut


class LoginRequest(BaseModel):
    username: str
    password: str
