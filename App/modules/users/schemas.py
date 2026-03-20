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
                "created_at": "2026-03-13T17:17:29.897877Z",
            }
        },
    )