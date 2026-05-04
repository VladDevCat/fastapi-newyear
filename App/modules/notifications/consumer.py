import logging
import os
import threading
from typing import Any

from redis.exceptions import RedisError

from app.common.cache import cache
from app.common.config import settings
from app.common.queue.rabbitmq import RabbitMQMessage, rabbitmq
from app.modules.notifications.email_service import EmailService

logger = logging.getLogger(__name__)


class UserRegisteredConsumer:
    def __init__(self) -> None:
        self.email = EmailService()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self.email.validate_config()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="rabbitmq-user-registered", daemon=True)
        self._thread.start()
        logger.info("RabbitMQ user registration consumer bootstrap started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        failures = 0
        while not self._stop_event.is_set():
            try:
                rabbitmq.consume(
                    queue=settings.QUEUE_USER_REGISTERED,
                    handler=self.handle_message,
                    stop_callback=self._stop_event.is_set,
                )
                failures = 0
            except Exception:
                if not self._stop_event.is_set():
                    failures += 1
                    logger.exception(
                        "RabbitMQ consumer crashed; reconnecting failure=%s max_failures=%s",
                        failures,
                        settings.RABBITMQ_CONSUMER_MAX_FAILURES,
                    )
                    if failures >= settings.RABBITMQ_CONSUMER_MAX_FAILURES:
                        logger.critical("RabbitMQ consumer cannot recover; exiting process for container restart")
                        os._exit(1)
                    self._stop_event.wait(3)

    def handle_message(self, message: RabbitMQMessage) -> None:
        content = message.content
        event_id = content.get("eventId")
        payload: dict[str, Any] = content.get("payload") or {}
        metadata: dict[str, Any] = content.get("metadata") or {}
        attempt = self._next_attempt(event_id, int(metadata.get("attempt") or 1)) if event_id else 1

        if not event_id or content.get("eventType") != "user.registered":
            logger.error("Unknown notification event moved to DLQ")
            rabbitmq.nack(message, requeue=False)
            return

        logger.info("Received RabbitMQ event event_id=%s type=%s attempt=%s", event_id, content.get("eventType"), attempt)

        if self._is_processed(event_id):
            logger.info("RabbitMQ event already processed; ack event_id=%s", event_id)
            rabbitmq.ack(message)
            return

        try:
            logger.info("Sending welcome email event_id=%s attempt=%s", event_id, attempt)
            self.email.send_welcome_email(
                to=payload["email"],
                display_name=payload.get("displayName"),
                user_id=payload["userId"],
            )
            self._mark_processed(event_id)
            cache.del_key(self._attempt_key(event_id))
            rabbitmq.ack(message)
            logger.info("Welcome email sent for event_id=%s", event_id)
        except Exception:
            if attempt >= settings.RABBITMQ_MAX_RETRIES:
                logger.exception("Welcome email failed after retries; event_id=%s moved to DLQ", event_id)
                cache.del_key(self._attempt_key(event_id))
                rabbitmq.nack(message, requeue=False)
                return

            rabbitmq.nack(message, requeue=True)
            logger.warning("Welcome email retry requested for event_id=%s next_attempt=%s", event_id, attempt + 1)

    def _processed_key(self, event_id: str) -> str:
        return cache.key("events", "processed", event_id)

    def _attempt_key(self, event_id: str) -> str:
        return cache.key("events", "attempts", event_id)

    def _is_processed(self, event_id: str) -> bool:
        return cache.get(self._processed_key(event_id)) is not None

    def _mark_processed(self, event_id: str) -> None:
        try:
            cache.client.set(self._processed_key(event_id), "1", ex=24 * 60 * 60, nx=True)
        except RedisError:
            logger.exception("Failed to mark event as processed")

    def _next_attempt(self, event_id: str, metadata_attempt: int) -> int:
        key = self._attempt_key(event_id)
        try:
            current = cache.client.incr(key)
            cache.client.expire(key, 24 * 60 * 60)
            return max(current, metadata_attempt)
        except RedisError:
            logger.exception("Failed to increment event attempt counter")
            return metadata_attempt


user_registered_consumer = UserRegisteredConsumer()
