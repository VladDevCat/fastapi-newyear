import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.item import HolidayItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_id(self, item_id: uuid.UUID) -> HolidayItem | None:
        stmt = select(HolidayItem).where(
            HolidayItem.id == item_id,
            HolidayItem.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_active_by_title_for_owner(
        self,
        title: str,
        owner_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> HolidayItem | None:
        stmt = select(HolidayItem).where(
            HolidayItem.title == title,
            HolidayItem.owner_id == owner_id,
            HolidayItem.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(HolidayItem.id != exclude_id)
        return self.db.scalar(stmt)

    def list_active_by_owner(
        self,
        owner_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[HolidayItem], int]:
        items_stmt = (
            select(HolidayItem)
            .where(
                HolidayItem.owner_id == owner_id,
                HolidayItem.deleted_at.is_(None),
            )
            .order_by(HolidayItem.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        count_stmt = select(func.count(HolidayItem.id)).where(
            HolidayItem.owner_id == owner_id,
            HolidayItem.deleted_at.is_(None),
        )

        items = list(self.db.scalars(items_stmt).all())
        total = self.db.scalar(count_stmt) or 0
        return items, total

    def create(self, data: dict) -> HolidayItem:
        item = HolidayItem(**data)
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def update(self, item: HolidayItem, data: dict) -> HolidayItem:
        for field, value in data.items():
            setattr(item, field, value)
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def soft_delete(self, item: HolidayItem) -> None:
        item.deleted_at = utc_now()
        self.db.add(item)
        self.db.flush()