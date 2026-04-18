import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    original_name: str
    object_key: str
    size: int
    mimetype: str
    bucket: str
    created_at: datetime = None
    updated_at: datetime = None
    deleted_at: datetime | None = None
