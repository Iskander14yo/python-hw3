from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LinkBase(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class LinkCreate(LinkBase):
    pass


class LinkUpdate(BaseModel):
    original_url: Optional[str] = None
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class Link(LinkBase):
    id: int
    short_code: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    clicks: int
    is_active: bool
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    clicks: int
