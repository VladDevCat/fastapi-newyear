import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.auth.token_model import SessionToken


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_token(
        self,
        *,
        token_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        token_type: str,
        token_hash: str,
        expires_at: datetime,
    ) -> SessionToken:
        token = SessionToken(
            id=token_id,
            session_id=session_id,
            user_id=user_id,
            token_type=token_type,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.flush()
        self.db.refresh(token)
        return token

    def get_valid_token(
        self,
        *,
        token_id: uuid.UUID,
        token_hash: str,
        token_type: str,
    ) -> SessionToken | None:
        stmt = select(SessionToken).where(
            SessionToken.id == token_id,
            SessionToken.token_hash == token_hash,
            SessionToken.token_type == token_type,
            SessionToken.is_revoked.is_(False),
            SessionToken.expires_at > utc_now(),
        )
        return self.db.scalar(stmt)

    def revoke_by_session_id(self, session_id: uuid.UUID) -> None:
        stmt = (
            update(SessionToken)
            .where(
                SessionToken.session_id == session_id,
                SessionToken.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                revoked_at=utc_now(),
            )
        )
        self.db.execute(stmt)

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(SessionToken)
            .where(
                SessionToken.user_id == user_id,
                SessionToken.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                revoked_at=utc_now(),
            )
        )
        self.db.execute(stmt)
