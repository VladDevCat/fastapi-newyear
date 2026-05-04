import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.common.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RabbitMQMessage:
    channel: BlockingChannel
    method: Basic.Deliver
    properties: BasicProperties
    content: dict[str, Any]


class RabbitMQService:
    def __init__(self) -> None:
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
        self.parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=30,
        )

    def _connect(self) -> pika.BlockingConnection:
        return pika.BlockingConnection(self.parameters)

    def declare_topology(self, channel: BlockingChannel) -> None:
        channel.exchange_declare(
            exchange=settings.RABBITMQ_EXCHANGE,
            exchange_type="direct",
            durable=True,
        )
        channel.exchange_declare(
            exchange=settings.RABBITMQ_DLX,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(
            queue=settings.QUEUE_USER_REGISTERED,
            durable=True,
            arguments={
                "x-dead-letter-exchange": settings.RABBITMQ_DLX,
                "x-dead-letter-routing-key": "user.registered",
            },
        )
        channel.queue_bind(
            queue=settings.QUEUE_USER_REGISTERED,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key="user.registered",
        )
        channel.queue_declare(queue=settings.QUEUE_USER_REGISTERED_DLQ, durable=True)
        channel.queue_bind(
            queue=settings.QUEUE_USER_REGISTERED_DLQ,
            exchange=settings.RABBITMQ_DLX,
            routing_key="user.registered",
        )

    def setup(self) -> None:
        connection = self._connect()
        try:
            channel = connection.channel()
            self.declare_topology(channel)
        finally:
            connection.close()

    def publish(
        self,
        exchange: str,
        routing_key: str,
        payload: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> None:
        connection = self._connect()
        try:
            channel = connection.channel()
            self.declare_topology(channel)
            channel.confirm_delivery()
            body = json.dumps(payload, default=str).encode("utf-8")
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2 if (options or {}).get("persistent", True) else 1,
                ),
                mandatory=True,
            )
            logger.info("Published RabbitMQ event type=%s routing_key=%s", payload.get("eventType"), routing_key)
        finally:
            connection.close()

    def consume(
        self,
        queue: str,
        handler: Callable[[RabbitMQMessage], None],
        stop_callback: Callable[[], bool],
    ) -> None:
        connection = self._connect()
        try:
            channel = connection.channel()
            self.declare_topology(channel)
            channel.basic_qos(prefetch_count=1)

            def callback(
                ch: BlockingChannel,
                method: Basic.Deliver,
                properties: BasicProperties,
                body: bytes,
            ) -> None:
                try:
                    content = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    logger.exception("Invalid JSON message moved to DLQ")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return

                handler(
                    RabbitMQMessage(
                        channel=ch,
                        method=method,
                        properties=properties,
                        content=content,
                    )
                )

            channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
            logger.info("RabbitMQ consumer started for queue=%s", queue)

            while not stop_callback():
                connection.process_data_events(time_limit=1)
        finally:
            try:
                if connection.is_open:
                    connection.close()
            except Exception:
                logger.exception("RabbitMQ connection close failed")

    def ack(self, message: RabbitMQMessage) -> None:
        message.channel.basic_ack(delivery_tag=message.method.delivery_tag)

    def nack(self, message: RabbitMQMessage, requeue: bool) -> None:
        message.channel.basic_nack(
            delivery_tag=message.method.delivery_tag,
            requeue=requeue,
        )


rabbitmq = RabbitMQService()
