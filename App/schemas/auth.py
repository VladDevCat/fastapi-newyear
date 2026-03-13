import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserPublicDTO


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-zА-Яа-я]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class RegisterDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordDTO(BaseModel):
    email: EmailStr


class ResetPasswordDTO(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AuthResponseDTO(BaseModel):
    user: UserPublicDTO


class MessageDTO(BaseModel):
    message: str


class ForgotPasswordResponseDTO(BaseModel):
    message: str
    reset_token: str | None = None


class AuthSessionResultDTO(BaseModel):
    user: UserPublicDTO
    access_token: str
    refresh_token: str