import os
import typing as tp

import pika
import structlog
from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel

logger = structlog.get_logger("toolset.event_bus.base")

NON_PERSISTENT_DELIVERY_MODE = 1
PERSISTENT_DELIVERY_MODE = 2

DEFAULT_PROPERTIES = pika.BasicProperties(
    content_type="application/json", delivery_mode=PERSISTENT_DELIVERY_MODE,
)

pika_parameters = pika.URLParameters(
    "amqp://{user}:{password}@{host}:{port}/?blocked_connection_timeout={timeout}".format(
        user=os.environ.get("RABBITMQ_USER", None),
        password=os.environ.get("RABBITMQ_PASSWORD", None),
        host=os.environ.get("RABBITMQ_HOST", None),
        port=os.environ.get("RABBITMQ_PORT", 5672),
        timeout=os.environ.get("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", 60),
    ),
)


class BaseMessageBus:
    """Base class for RabbitMQ pub/sub."""

    def __init__(
        self,
        url_params: pika.URLParameters = pika_parameters,
        pika_props: pika.BasicProperties = DEFAULT_PROPERTIES,
    ) -> None:
        """Init."""
        self.url_params = url_params
        self.properties = pika_props

        self._connection: tp.Optional[pika.BlockingConnection] = None
        self._channel: tp.Optional[BlockingChannel] = None
        self._in_ctx = False

    def __enter__(self) -> "BaseMessageBus":
        """Create connection."""
        self._connection = self._get_rabbit_connection()
        self._channel = self._connection.channel()
        self._in_ctx = True

        logger.debug("Connection & channel established in ctx")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection."""
        self.close()
        self._in_ctx = False

    def close(self) -> None:
        """Close channel and connection."""
        if self._channel and self._channel.is_open:
            self._channel.close()
        if self._connection and self._connection.is_open:
            self._connection.close()

        logger.debug("Connection & channel closed.")

    def _get_connection(self) -> BlockingConnection:
        if self._in_ctx:
            connection = tp.cast(BlockingConnection, self._connection)
            logger.debug("Takes existing connection (ctx)")
        else:
            connection = self._get_rabbit_connection()
            logger.debug("Created a new connection")
        return connection

    def _get_channel(self, connection: tp.Optional[BlockingConnection] = None) -> BlockingChannel:
        """Init a new instance of BlockingChannel."""
        if self._in_ctx and self._channel:
            channel: BlockingChannel = self._channel
        elif connection:
            channel = connection.channel()
        else:
            connection = self._get_connection()
            channel = connection.channel()

        return channel

    def _get_rabbit_connection(self) -> pika.BlockingConnection:
        return pika.BlockingConnection(self.url_params)
