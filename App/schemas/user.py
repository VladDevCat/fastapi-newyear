import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublicDTO(BaseModel):
    id: uuid.UUID
    email: EmailStr
    phone: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)