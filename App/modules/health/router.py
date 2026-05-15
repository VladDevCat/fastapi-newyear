from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from app.common.cache import cache
from app.common.db import client
from app.common.queue.rabbitmq import rabbitmq
from app.modules.storage.service import get_minio_client

router = APIRouter(prefix="/health", tags=["Health"])


def _ok() -> dict[str, Any]:
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("", summary="Общий статус приложения")
def health():
    return _ok()


@router.get("/live", summary="Liveness probe")
def live():
    return _ok()


@router.get("/ready", summary="Readiness probe")
def ready():
    checks: dict[str, dict[str, str]] = {}

    try:
        client.admin.command("ping")
        checks["mongo"] = {"status": "ok"}
    except PyMongoError as exc:
        checks["mongo"] = {"status": "error", "detail": str(exc)}

    try:
        cache.client.ping()
        checks["redis"] = {"status": "ok"}
    except RedisError as exc:
        checks["redis"] = {"status": "error", "detail": str(exc)}

    try:
        rabbitmq.ping()
        checks["rabbitmq"] = {"status": "ok"}
    except Exception as exc:
        checks["rabbitmq"] = {"status": "error", "detail": str(exc)}

    try:
        get_minio_client().list_buckets()
        checks["minio"] = {"status": "ok"}
    except Exception as exc:
        checks["minio"] = {"status": "error", "detail": str(exc)}

    is_ready = all(check["status"] == "ok" for check in checks.values())
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
