import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SessionToken:
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    token_type: str
    token_hash: str
    expires_at: datetime
    is_revoked: bool = False
    created_at: datetime = None
    revoked_at: datetime | None = None
