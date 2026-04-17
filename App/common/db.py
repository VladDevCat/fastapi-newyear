from collections.abc import Generator

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import OperationFailure

from app.common.config import settings

client: MongoClient = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)


class MongoUnitOfWork:
    def __init__(self, database: Database):
        self.database = database

    def collection(self, name: str):
        return self.database[name]

    def commit(self) -> None:
        return None

    def refresh(self, _document) -> None:
        return None

    def close(self) -> None:
        return None


def get_database() -> Database:
    return client[settings.MONGO_DB_NAME]


def get_db() -> Generator[MongoUnitOfWork, None, None]:
    db = MongoUnitOfWork(get_database())
    try:
        yield db
    finally:
        db.close()


def create_indexes() -> None:
    database = get_database()

    database.users.create_index("email", unique=True)
    database.users.update_many({"yandex_id": None}, {"$unset": {"yandex_id": ""}})
    try:
        database.users.drop_index("yandex_id_1")
    except OperationFailure:
        pass
    database.users.create_index(
        "yandex_id",
        unique=True,
        partialFilterExpression={"yandex_id": {"$type": "string"}},
    )
    database.users.create_index("deleted_at")

    database.holiday_items.create_index([("owner_id", 1), ("deleted_at", 1), ("created_at", -1)])
    database.holiday_items.create_index([("owner_id", 1), ("title", 1), ("deleted_at", 1)])

    database.session_tokens.create_index("token_hash", unique=True)
    database.session_tokens.create_index([("session_id", 1), ("is_revoked", 1)])
    database.session_tokens.create_index([("user_id", 1), ("is_revoked", 1)])
    database.session_tokens.create_index("expires_at")

    database.password_reset_tokens.create_index("token_hash", unique=True)
    database.password_reset_tokens.create_index([("user_id", 1), ("is_used", 1)])
    database.password_reset_tokens.create_index("expires_at")

    database.oauth_states.create_index("state_hash", unique=True)
    database.oauth_states.create_index([("provider", 1), ("is_used", 1)])
    database.oauth_states.create_index("expires_at")
