import uuid
from datetime import datetime

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.auth.token_model import SessionToken


class SessionTokenRepository:
    def __init__(self, db):
        self.collection = db.collection("session_tokens")

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
            created_at=utc_now(),
        )
        self.collection.insert_one(dataclass_to_document(token))
        return token

    def get_valid_token(
        self,
        *,
        token_id: uuid.UUID,
        token_hash: str,
        token_type: str,
    ) -> SessionToken | None:
        document = self.collection.find_one(
            {
                "_id": document_id(token_id),
                "token_hash": token_hash,
                "token_type": token_type,
                "is_revoked": False,
                "expires_at": {"$gt": utc_now()},
            }
        )
        return document_to_dataclass(SessionToken, document)

    def list_valid_tokens_by_session(
        self,
        *,
        session_id: uuid.UUID,
        token_type: str,
    ) -> list[SessionToken]:
        cursor = self.collection.find(
            {
                "session_id": document_id(session_id),
                "token_type": token_type,
                "is_revoked": False,
                "expires_at": {"$gt": utc_now()},
            }
        )
        return [document_to_dataclass(SessionToken, document) for document in cursor]

    def revoke_by_session_id(self, session_id: uuid.UUID) -> None:
        self.collection.update_many(
            {
                "session_id": document_id(session_id),
                "is_revoked": False,
            },
            {
                "$set": {
                    "is_revoked": True,
                    "revoked_at": utc_now(),
                }
            },
        )

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self.collection.update_many(
            {
                "user_id": document_id(user_id),
                "is_revoked": False,
            },
            {
                "$set": {
                    "is_revoked": True,
                    "revoked_at": utc_now(),
                }
            },
        )
