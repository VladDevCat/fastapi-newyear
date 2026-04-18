import uuid

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.storage.model import FileRecord


class FileRepository:
    def __init__(self, db):
        self.collection = db.collection("files")

    def get_active_by_id(self, file_id: uuid.UUID) -> FileRecord | None:
        document = self.collection.find_one(
            {
                "_id": document_id(file_id),
                "deleted_at": None,
            }
        )
        return document_to_dataclass(FileRecord, document)

    def get_active_by_id_for_user(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> FileRecord | None:
        document = self.collection.find_one(
            {
                "_id": document_id(file_id),
                "user_id": document_id(user_id),
                "deleted_at": None,
            }
        )
        return document_to_dataclass(FileRecord, document)

    def create(self, data: dict) -> FileRecord:
        now = utc_now()
        file_record = FileRecord(
            id=data.get("id", uuid.uuid4()),
            user_id=data["user_id"],
            original_name=data["original_name"],
            object_key=data["object_key"],
            size=data["size"],
            mimetype=data["mimetype"],
            bucket=data["bucket"],
            created_at=data.get("created_at", now),
            updated_at=data.get("updated_at", now),
            deleted_at=data.get("deleted_at"),
        )
        self.collection.insert_one(dataclass_to_document(file_record))
        return file_record

    def soft_delete(self, file_record: FileRecord) -> None:
        now = utc_now()
        self.collection.update_one(
            {"_id": document_id(file_record.id)},
            {
                "$set": {
                    "deleted_at": now,
                    "updated_at": now,
                }
            },
        )
