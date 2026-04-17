import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    id: uuid.UUID
    email: str
    phone: str | None = None
    password_hash: str | None = None
    password_salt: str | None = None
    yandex_id: str | None = None
    created_at: datetime = None
    updated_at: datetime = None
    deleted_at: datetime | None = None
