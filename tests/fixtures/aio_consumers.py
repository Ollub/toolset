import json
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock

from toolset.typing_helpers import JSON


@pytest.fixture()
def robust_connection_mock(mocker, connection_mock):
    """Mock aio_pika.connect_robust method, returning connection object."""
    return mocker.patch(
        "toolset.event_bus.aio.consumers.aio_pika.connect_robust",
        CoroutineMock(return_value=connection_mock),
    )


@pytest.fixture()
def channel_mock(queue_mock, exchange_mock_factory):
    """Channel mock."""
    channel = MagicMock()

    async def _close():
        channel.is_closed = True

    channel.is_closed = False
    channel.close = _close
    channel.declare_queue = CoroutineMock(return_value=queue_mock)
    channel.declare_exchange = CoroutineMock(side_effect=exchange_mock_factory)
    channel.set_qos = CoroutineMock()

    return channel


@pytest.fixture()
def exchange_mock_factory():
    """Exchange mock factory."""

    def factory(*args, **kwargs):
        exchange = MagicMock(*args, **kwargs)
        exchange.publish = CoroutineMock()
        return exchange

    return factory


@pytest.fixture()
def connection_mock(channel_mock):
    """Connection mock."""
    connection = MagicMock()

    async def _close():
        connection.is_closed = True

    connection.is_closed = False
    connection.channel = CoroutineMock(return_value=channel_mock)
    connection.close = _close

    return connection


@pytest.fixture()
def queue_mock():
    """Queue mock."""
    queue = CoroutineMock()
    queue.bind = CoroutineMock()
    return queue


@pytest.fixture()
def full_queue_factory(queue_mock):
    """Put message in queue."""

    def factory(messages):
        queue_mock.iterator = QueueIteratorMock(messages)
        return queue_mock

    return factory


@pytest.fixture()
def rabbit_message_factory():
    """Message factory. Return coroutine mock object."""

    def factory(payload: JSON, routing_key: str):
        message = CoroutineMock()
        message.body = json.dumps(payload).encode()
        message.routing_key = routing_key
        return message

    return factory


class QueueIteratorMock:
    """Mocked queue iterator."""

    def __init__(self, messages):
        """Init."""
        self._messages_gen = (msg for msg in messages)

    def __call__(self, *args, **kwargs):
        """Call."""
        return self

    async def __aenter__(self):
        """Enter."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit."""

    def __aiter__(self):
        """Aiter."""
        return self

    async def __anext__(self):
        """Iterate over messages."""
        try:
            return next(self._messages_gen)
        except StopIteration:  # noqa: WPS329 useless except case
            raise StopAsyncIteration
