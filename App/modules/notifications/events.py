import uuid
import logging
from datetime import datetime, timezone

from app.common.config import settings
from app.common.queue.rabbitmq import rabbitmq
from app.modules.users.model import User

logger = logging.getLogger(__name__)


def publish_user_registered_event(user: User) -> None:
    payload = {
        "eventId": str(uuid.uuid4()),
        "eventType": "user.registered",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "userId": str(user.id),
            "email": user.email,
            "displayName": user.display_name or user.email.split("@", 1)[0],
        },
        "metadata": {
            "attempt": 1,
            "sourceService": "auth-service",
        },
    }
    rabbitmq.publish(
        exchange=settings.RABBITMQ_EXCHANGE,
        routing_key="user.registered",
        payload=payload,
        options={"persistent": True},
    )
    logger.info(
        "User registered event published event_id=%s user_id=%s routing_key=user.registered",
        payload["eventId"],
        user.id,
    )
