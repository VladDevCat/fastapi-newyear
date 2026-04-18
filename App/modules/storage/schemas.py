import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileResponseDTO(BaseModel):
    id: uuid.UUID = Field(..., examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    original_name: str = Field(..., examples=["avatar.png"])
    size: int = Field(..., examples=[128000])
    mimetype: str = Field(..., examples=["image/png"])
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "original_name": "avatar.png",
                "size": 128000,
                "mimetype": "image/png",
                "created_at": "2026-04-17T19:30:00Z",
                "updated_at": "2026-04-17T19:30:00Z",
            }
        },
    )


class ProfileUpdateDTO(BaseModel):
    display_name: str | None = Field(None, max_length=120, examples=["Maria"])
    bio: str | None = Field(None, max_length=500, examples=["Preparing for the New Year"])
    avatar_file_id: uuid.UUID | None = Field(
        None,
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )


class ProfileResponseDTO(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None = None
    display_name: str | None = None
    bio: str | None = None
    avatar_file_id: uuid.UUID | None = None
    avatar: FileResponseDTO | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                "email": "user@example.com",
                "phone": None,
                "display_name": "Maria",
                "bio": "Preparing for the New Year",
                "avatar_file_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "avatar": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "original_name": "avatar.png",
                    "size": 128000,
                    "mimetype": "image/png",
                    "created_at": "2026-04-17T19:30:00Z",
                    "updated_at": "2026-04-17T19:30:00Z",
                },
                "created_at": "2026-04-17T19:30:00Z",
            }
        },
    )
