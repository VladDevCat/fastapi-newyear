import uuid

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.auth.reset_token_model import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, db):
        self.collection = db.collection("password_reset_tokens")

    def create(self, data: dict) -> PasswordResetToken:
        token = PasswordResetToken(
            id=data.get("id", uuid.uuid4()),
            user_id=data["user_id"],
            token_hash=data["token_hash"],
            expires_at=data["expires_at"],
            is_used=data.get("is_used", False),
            created_at=data.get("created_at", utc_now()),
        )
        self.collection.insert_one(dataclass_to_document(token))
        return token

    def get_valid_token(self, token_hash: str) -> PasswordResetToken | None:
        document = self.collection.find_one(
            {
                "token_hash": token_hash,
                "is_used": False,
                "expires_at": {"$gt": utc_now()},
            }
        )
        return document_to_dataclass(PasswordResetToken, document)

    def mark_used(self, token: PasswordResetToken) -> PasswordResetToken:
        self.collection.update_one(
            {"_id": document_id(token.id)},
            {"$set": {"is_used": True}},
        )
        return document_to_dataclass(
            PasswordResetToken,
            self.collection.find_one({"_id": document_id(token.id)}),
        )

    def mark_all_used_for_user(self, user_id):
        self.collection.update_many(
            {
                "user_id": document_id(user_id),
                "is_used": False,
            },
            {"$set": {"is_used": True}},
        )
