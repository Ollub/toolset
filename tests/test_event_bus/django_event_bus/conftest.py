import json
from unittest.mock import MagicMock

import pytest

BLOCKING_DELIVERY_TAG = "tag"


@pytest.fixture()
def blocking_connection_mock(mocker, connection_mock):
    """Mock blocking_connection method, returning connection object."""
    return mocker.patch(
        "toolset.event_bus.django.base.pika.BlockingConnection", return_value=connection_mock,
    )


@pytest.fixture()
def channel_mock():
    """Channel mock."""
    channel_mock = MagicMock()

    def _close():
        channel_mock.is_closed = True

    channel_mock.is_closed = False
    channel_mock.close = MagicMock(side_effect=_close)

    def _basic_consume(queue, on_message_callback):
        channel_mock.on_message_callback = on_message_callback

    channel_mock.basic_consume = MagicMock(side_effect=_basic_consume)

    return channel_mock


@pytest.fixture()
def connection_mock(channel_mock):
    """Connection mock."""
    connection_mock = MagicMock()

    def _close():
        connection_mock.is_closed = True

    connection_mock.is_closed = False
    connection_mock.close = MagicMock(side_effect=_close)

    connection_mock.channel = MagicMock(return_value=channel_mock)

    return connection_mock


@pytest.fixture()
def message_factory(connection_mock, channel_mock):
    """Message factory."""

    def factory(message, routing_key):
        def _on_message_callback():
            message_mock = MagicMock()
            message_mock.routing_key = routing_key
            message_mock.delivery_tag = BLOCKING_DELIVERY_TAG

            message_body = json.dumps(message).encode()

            channel_mock.on_message_callback(channel_mock, message_mock, MagicMock(), message_body)

        channel_mock.start_consuming = MagicMock(side_effect=_on_message_callback)

    return factory
