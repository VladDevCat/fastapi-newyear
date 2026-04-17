import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublicDTO(BaseModel):
    id: uuid.UUID = Field(
        ...,
        description="Уникальный идентификатор пользователя",
        examples=["cf48ed93-fa37-49f7-b71b-04d8bf477e4f"],
    )
    email: EmailStr = Field(
        ...,
        description="Email пользователя",
        examples=["user@example.com"],
    )
    phone: str | None = Field(
        None,
        description="Телефон пользователя, если указан",
        examples=["+79991234567"],
    )
    display_name: str | None = Field(
        None,
        description="Public display name",
        examples=["Maria"],
    )
    bio: str | None = Field(
        None,
        description="Short profile text",
        examples=["Preparing for the New Year"],
    )
    avatar_file_id: uuid.UUID | None = Field(
        None,
        description="Avatar file metadata id",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания пользователя",
        examples=["2026-03-13T17:17:29.897877Z"],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                "email": "user@example.com",
                "phone": None,
                "display_name": "Maria",
                "bio": "Preparing for the New Year",
                "avatar_file_id": None,
                "created_at": "2026-03-13T17:17:29.897877Z",
            }
        },
    )
