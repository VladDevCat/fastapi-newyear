import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemStatus(str, Enum):
    planned = "planned"
    purchased = "purchased"
    done = "done"


@dataclass
class HolidayItem:
    id: uuid.UUID
    owner_id: uuid.UUID | None
    title: str
    description: str
    status: str = ItemStatus.planned.value
    created_at: datetime = None
    updated_at: datetime = None
    deleted_at: datetime | None = None
