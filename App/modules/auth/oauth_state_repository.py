import uuid

from app.common.mongo_helpers import dataclass_to_document, document_id, document_to_dataclass, utc_now
from app.modules.auth.oauth_state_model import OAuthState


class OAuthStateRepository:
    def __init__(self, db):
        self.collection = db.collection("oauth_states")

    def create(self, data: dict) -> OAuthState:
        state = OAuthState(
            id=data.get("id", uuid.uuid4()),
            provider=data["provider"],
            state_hash=data["state_hash"],
            expires_at=data["expires_at"],
            is_used=data.get("is_used", False),
            created_at=data.get("created_at", utc_now()),
        )
        self.collection.insert_one(dataclass_to_document(state))
        return state

    def get_valid_state(self, provider: str, state_hash: str) -> OAuthState | None:
        document = self.collection.find_one(
            {
                "provider": provider,
                "state_hash": state_hash,
                "is_used": False,
                "expires_at": {"$gt": utc_now()},
            }
        )
        return document_to_dataclass(OAuthState, document)

    def mark_used(self, state: OAuthState) -> OAuthState:
        self.collection.update_one(
            {"_id": document_id(state.id)},
            {"$set": {"is_used": True}},
        )
        return document_to_dataclass(OAuthState, self.collection.find_one({"_id": document_id(state.id)}))
