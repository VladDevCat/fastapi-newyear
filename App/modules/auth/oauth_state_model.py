import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OAuthState:
    id: uuid.UUID
    provider: str
    state_hash: str
    expires_at: datetime
    is_used: bool = False
    created_at: datetime = None
