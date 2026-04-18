import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, TypeVar

T = TypeVar("T")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def uuid_to_str(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def str_to_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def document_id(value: uuid.UUID | str) -> str:
    return str(value)


def dataclass_to_document(value: Any) -> dict:
    data = asdict(value) if is_dataclass(value) else dict(value)
    data["_id"] = str(data.pop("id"))
    for key in ("owner_id", "user_id", "session_id", "avatar_file_id"):
        if key in data:
            data[key] = uuid_to_str(data[key])
    return data


def document_to_dataclass(model: type[T], document: dict | None) -> T | None:
    if document is None:
        return None

    data = dict(document)
    data["id"] = str_to_uuid(data.pop("_id"))
    for key in ("owner_id", "user_id", "session_id", "avatar_file_id"):
        if key in data:
            data[key] = str_to_uuid(data[key])
    return model(**data)
