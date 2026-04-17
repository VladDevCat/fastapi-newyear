import uuid

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.items.model import HolidayItem


class ItemRepository:
    def __init__(self, db):
        self.collection = db.collection("holiday_items")

    def get_active_by_id(self, item_id: uuid.UUID) -> HolidayItem | None:
        document = self.collection.find_one(
            {
                "_id": document_id(item_id),
                "deleted_at": None,
            }
        )
        return document_to_dataclass(HolidayItem, document)

    def get_active_by_title_for_owner(
        self,
        title: str,
        owner_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> HolidayItem | None:
        query = {
            "title": title,
            "owner_id": document_id(owner_id),
            "deleted_at": None,
        }
        if exclude_id is not None:
            query["_id"] = {"$ne": document_id(exclude_id)}
        return document_to_dataclass(HolidayItem, self.collection.find_one(query))

    def list_active_by_owner(
        self,
        owner_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[HolidayItem], int]:
        query = {
            "owner_id": document_id(owner_id),
            "deleted_at": None,
        }
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        items = [document_to_dataclass(HolidayItem, document) for document in cursor]
        total = self.collection.count_documents(query)
        return items, total

    def create(self, data: dict) -> HolidayItem:
        now = utc_now()
        item = HolidayItem(
            id=data.get("id", uuid.uuid4()),
            owner_id=data.get("owner_id"),
            title=data["title"],
            description=data["description"],
            status=data.get("status") or "planned",
            created_at=data.get("created_at", now),
            updated_at=data.get("updated_at", now),
            deleted_at=data.get("deleted_at"),
        )
        self.collection.insert_one(dataclass_to_document(item))
        return item

    def update(self, item: HolidayItem, data: dict) -> HolidayItem:
        update_data = {**data, "updated_at": utc_now()}
        if "owner_id" in update_data:
            update_data["owner_id"] = document_id(update_data["owner_id"])
        self.collection.update_one(
            {"_id": document_id(item.id)},
            {"$set": update_data},
        )
        return self.get_active_by_id(item.id)

    def soft_delete(self, item: HolidayItem) -> None:
        now = utc_now()
        self.collection.update_one(
            {"_id": document_id(item.id)},
            {"$set": {"deleted_at": now, "updated_at": now}},
        )
