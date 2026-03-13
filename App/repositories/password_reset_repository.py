from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PasswordResetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PasswordResetToken:
        token = PasswordResetToken(**data)
        self.db.add(token)
        self.db.flush()
        self.db.refresh(token)
        return token

    def get_valid_token(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
            PasswordResetToken.expires_at > utc_now(),
        )
        return self.db.scalar(stmt)

    def mark_used(self, token: PasswordResetToken) -> PasswordResetToken:
        token.is_used = True
        self.db.add(token)
        self.db.flush()
        self.db.refresh(token)
        return token

    def mark_all_used_for_user(self, user_id):
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.is_used.is_(False),
            )
            .values(is_used=True)
        )
        self.db.execute(stmt)