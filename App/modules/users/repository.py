import uuid

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.users.model import User


class UserRepository:
    def __init__(self, db):
        self.collection = db.collection("users")

    def get_active_by_email(self, email: str) -> User | None:
        document = self.collection.find_one(
            {
                "email": email,
                "deleted_at": None,
            }
        )
        return document_to_dataclass(User, document)

    def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        document = self.collection.find_one(
            {
                "_id": document_id(user_id),
                "deleted_at": None,
            }
        )
        return document_to_dataclass(User, document)

    def get_by_yandex_id(self, yandex_id: str) -> User | None:
        document = self.collection.find_one(
            {
                "yandex_id": yandex_id,
                "deleted_at": None,
            }
        )
        return document_to_dataclass(User, document)

    def create(self, data: dict) -> User:
        now = utc_now()
        user = User(
            id=data.get("id", uuid.uuid4()),
            email=data["email"],
            phone=data.get("phone"),
            password_hash=data.get("password_hash"),
            password_salt=data.get("password_salt"),
            yandex_id=data.get("yandex_id"),
            created_at=data.get("created_at", now),
            updated_at=data.get("updated_at", now),
            deleted_at=data.get("deleted_at"),
        )
        document = dataclass_to_document(user)
        if document.get("yandex_id") is None:
            document.pop("yandex_id", None)
        self.collection.insert_one(document)
        return user

    def update(self, user: User, data: dict) -> User:
        update_data = {**data, "updated_at": utc_now()}
        self.collection.update_one(
            {"_id": document_id(user.id)},
            {"$set": update_data},
        )
        return self.get_active_by_id(user.id)
