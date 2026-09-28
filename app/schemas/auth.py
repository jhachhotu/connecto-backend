from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str
    avatar: Optional[str] = None


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    exp: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: str = Field(default="customer", pattern="^(customer|worker|admin)$")
    avatar: Optional[str] = None
    
    # If registering as worker
    category_id: Optional[str] = None
    experience_years: Optional[int] = 3


class GoogleAuthRequest(BaseModel):
    id_token: str
    role: Optional[str] = "customer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
