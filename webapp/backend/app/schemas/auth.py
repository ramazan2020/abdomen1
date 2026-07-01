from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str  # "admin" | "doctor"


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
