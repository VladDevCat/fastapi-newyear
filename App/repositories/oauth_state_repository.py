from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_state import OAuthState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OAuthStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> OAuthState:
        state = OAuthState(**data)
        self.db.add(state)
        self.db.flush()
        self.db.refresh(state)
        return state

    def get_valid_state(self, provider: str, state_hash: str) -> OAuthState | None:
        stmt = select(OAuthState).where(
            OAuthState.provider == provider,
            OAuthState.state_hash == state_hash,
            OAuthState.is_used.is_(False),
            OAuthState.expires_at > utc_now(),
        )
        return self.db.scalar(stmt)

    def mark_used(self, state: OAuthState) -> OAuthState:
        state.is_used = True
        self.db.add(state)
        self.db.flush()
        self.db.refresh(state)
        return state