import json
import socket
import typing as tp

import pika
import structlog
from pika.adapters.utils.connection_workflow import AMQPConnectorException
from pika.channel import Channel
from pika.exceptions import (
    AMQPConnectionError,
    AMQPError,
    ChannelError,
    ProbableAuthenticationError,
)

from toolset.decorators import retry
from toolset.event_bus.django.base import DEFAULT_PROPERTIES, BaseMessageBus, pika_parameters
from toolset.typing_helpers import JSON

try:
    from rest_framework.utils.encoders import JSONEncoder
except ImportError:
    JSONEncoder = None


logger = structlog.get_logger("toolset.event_bus.producers")


class ChannelMock:
    """Channel mock."""

    def __init__(self, *args, **kwargs) -> None:
        """Init mock."""
        self._closed = False
        self.is_open = True

    def basic_publish(self, *args, **kwargs) -> None:
        """Mock of basic publish."""
        logger.info("Publish called", args=args, kwargs=kwargs)

    def close(self) -> None:
        """Close mock."""
        if self._closed:
            raise ValueError
        self._closed = True
        self.is_open = False


class ConnectionMock:
    """Connection mock."""

    def __init__(self, *args, **kwargs) -> None:
        """Init mock."""
        self._closed = False
        self.is_open = True

    def channel(self, *args, **kwargs) -> ChannelMock:
        """Channel mock."""
        return ChannelMock()

    def close(self) -> None:
        """Close mock."""
        if self._closed:
            raise ValueError
        self._closed = True
        self.is_open = False


class BaseProducer(BaseMessageBus):
    """Base event producer."""

    exchange: str
    json_encoder = JSONEncoder

    def __init__(
        self,
        url_params: pika.URLParameters = pika_parameters,
        pika_props: pika.BasicProperties = DEFAULT_PROPERTIES,
    ) -> None:
        """Init."""
        super().__init__(url_params, pika_props)

        self._exchange_declared = False

    @retry(
        AMQPConnectorException,
        AMQPConnectionError,
        AMQPError,
        ChannelError,
        ProbableAuthenticationError,
        socket.gaierror,
        attempts=5,
        wait_time_seconds=2,
        backoff=3,
    )
    def publish(self, routing_key: str, body: JSON) -> None:
        """Publish event."""
        if self._in_ctx:
            connection = tp.cast(pika.BlockingConnection, self._connection)
        else:
            connection = self._get_rabbit_connection()
        channel: Channel = connection.channel()

        try:
            channel.basic_publish(
                self.exchange,
                routing_key,
                json.dumps(body, ensure_ascii=False, cls=self.json_encoder).encode("utf-8"),
                self.properties,
            )
        except Exception as exc:
            logger.exception(exc)
        finally:
            if not self._in_ctx:
                if channel.is_open:
                    channel.close()
                if connection.is_open:
                    connection.close()
