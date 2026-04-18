import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.common.config import settings

logger = logging.getLogger(__name__)


class RedisCacheService:
    def __init__(self) -> None:
        self.client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def key(self, *parts: Any) -> str:
        safe_parts = [str(part).strip(":") for part in parts if part is not None]
        return ":".join([settings.REDIS_KEY_PREFIX, *safe_parts])

    def is_available(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError as exc:
            logger.warning("Redis unavailable: %s", exc)
            return False

    def get(self, key: str) -> Any | None:
        try:
            raw_value = self.client.get(key)
        except RedisError as exc:
            logger.warning("Redis get failed for %s: %s", key, exc)
            return None

        if raw_value is None:
            return None

        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return raw_value

    def set(self, key: str, value: Any, ttl: int) -> bool:
        if ttl <= 0:
            raise ValueError("Redis keys must always be written with positive TTL")

        try:
            payload = json.dumps(value, default=str)
            return bool(self.client.set(name=key, value=payload, ex=ttl))
        except RedisError as exc:
            logger.warning("Redis set failed for %s: %s", key, exc)
            return False

    def del_key(self, key: str) -> int:
        try:
            return int(self.client.delete(key))
        except RedisError as exc:
            logger.warning("Redis delete failed for %s: %s", key, exc)
            return 0

    def delByPattern(self, pattern: str) -> int:
        deleted = 0
        try:
            for key in self.client.scan_iter(match=pattern):
                deleted += int(self.client.delete(key))
        except RedisError as exc:
            logger.warning("Redis pattern delete failed for %s: %s", pattern, exc)
        return deleted


setattr(RedisCacheService, "del", RedisCacheService.del_key)

cache = RedisCacheService()
