import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.users.schemas import UserPublicDTO


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-zА-Яа-я]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class RegisterDTO(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Email для регистрации",
        examples=["maria.test@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль пользователя. Должен содержать минимум 8 символов, буквы и цифры.",
        examples=["Winter2026"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "maria.test@example.com",
                "password": "Winter2026",
            }
        }
    }


class LoginDTO(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя", examples=["maria.test@example.com"])
    password: str = Field(..., min_length=8, max_length=128, description="Пароль пользователя", examples=["Winter2026"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "maria.test@example.com",
                "password": "Winter2026",
            }
        }
    }


class ForgotPasswordDTO(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя для сброса пароля", examples=["maria.test@example.com"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "maria.test@example.com",
            }
        }
    }


class ResetPasswordDTO(BaseModel):
    token: str = Field(
        ...,
        min_length=20,
        max_length=512,
        description="Токен сброса пароля",
        examples=["reset_token_example_1234567890"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль",
        examples=["NewPass2026"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "reset_token_example_1234567890",
                "new_password": "NewPass2026",
            }
        }
    }


class AuthResponseDTO(BaseModel):
    user: UserPublicDTO = Field(..., description="Публичный профиль авторизованного пользователя")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                    "email": "user@example.com",
                    "phone": None,
                    "created_at": "2026-03-13T17:17:29.897877Z",
                }
            }
        }
    }


class MessageDTO(BaseModel):
    message: str = Field(..., description="Текстовое сообщение о результате операции", examples=["Logged out successfully"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Logged out successfully"
            }
        }
    }


class ForgotPasswordResponseDTO(BaseModel):
    message: str = Field(..., description="Сообщение о результате запроса на сброс пароля")
    reset_token: str | None = Field(
        None,
        description="Отладочный reset token. Возвращается только если AUTH_DEBUG_RETURN_RESET_TOKEN=true",
        examples=["reset_token_example_1234567890"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "If the account exists, a reset instruction has been generated",
                "reset_token": None,
            }
        }
    }


class AuthSessionResultDTO(BaseModel):
    user: UserPublicDTO
    access_token: str
    refresh_token: str
