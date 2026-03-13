import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_by_yandex_id(self, yandex_id: str) -> User | None:
        stmt = select(User).where(
            User.yandex_id == yandex_id,
            User.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def create(self, data: dict) -> User:
        user = User(**data)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def update(self, user: User, data: dict) -> User:
        for field, value in data.items():
            setattr(user, field, value)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user