import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    tipo: str       # "equipo" | "jugador"
    entity_id: str  # slug


class FavoriteResponse(BaseModel):
    id: int
    tipo: str
    entity_id: str
    created_at: datetime

    class Config:
        from_attributes = True
