from unittest.mock import MagicMock

import pytest
from structlog.testing import capture_logs

from toolset.event_bus.django import BaseConsumer
from toolset.event_bus.django.consumers.constants import CONSUMER_CONNECTION_PREFETCH_COUNT
from tests.test_event_bus.django_event_bus.conftest import BLOCKING_DELIVERY_TAG

queue_name = "foo_queue"
exchange_name = "foo_exchange"
routing_key = "bar.updated"


def test_client_connected(  # noqa: WPS218  Found too many assert
    blocking_connection_mock, connection_mock, channel_mock,
):
    """Test connection established and closed then."""
    consumer = BaseConsumer(queue_name, MagicMock())

    with capture_logs() as cap_logs:
        consumer.start_consuming(exchange_name, [routing_key])

        connection_mock.channel.assert_called_once()

        channel_mock.basic_qos.assert_called_once_with(
            prefetch_count=CONSUMER_CONNECTION_PREFETCH_COUNT,
        )

        assert cap_logs[0] == {
            "log_level": "debug",
            "event": "Created a new connection",
        }
        assert cap_logs[1] == {
            "log_level": "debug",
            "event": "Created a new channel with prefetch_count",
            "prefetch_count": CONSUMER_CONNECTION_PREFETCH_COUNT,
        }
        assert cap_logs[2] == {
            "log_level": "debug",
            "event": "Declared a new queue to consuming",
            "exchange_name": exchange_name,
            "routing_keys": [routing_key],
            "queue_name": queue_name,
        }
        assert cap_logs[3] == {
            "log_level": "debug",
            "event": "Start consuming",
        }
        assert cap_logs[4] == {
            "log_level": "debug",
            "event": "Channel & connection closed (without ctx)",
        }


def test_client_connected_in_ctx(  # noqa: WPS218 Found too many assert
    blocking_connection_mock, connection_mock, channel_mock,
):
    """Test connection established and closed then in ctx."""
    with capture_logs() as cap_logs:

        with BaseConsumer(queue_name, MagicMock()) as consumer:
            consumer.start_consuming(exchange_name, [routing_key])

            connection_mock.channel.assert_called_once()

            assert cap_logs[0] == {
                "log_level": "debug",
                "event": "Connection & channel established in ctx",
            }
            assert cap_logs[1] == {
                "log_level": "debug",
                "event": "Takes existing connection (ctx)",
            }
            assert cap_logs[2] == {
                "log_level": "debug",
                "event": "Created a new channel with prefetch_count",
                "prefetch_count": CONSUMER_CONNECTION_PREFETCH_COUNT,
            }
            assert cap_logs[3] == {
                "log_level": "debug",
                "event": "Declared a new queue to consuming",
                "exchange_name": exchange_name,
                "routing_keys": [routing_key],
                "queue_name": queue_name,
            }
            assert cap_logs[4] == {
                "log_level": "debug",
                "event": "Start consuming",
            }

        channel_mock.basic_qos.assert_called_once_with(
            prefetch_count=CONSUMER_CONNECTION_PREFETCH_COUNT,
        )

        assert cap_logs[-1] == {
            "log_level": "debug",
            "event": "Connection & channel closed.",
        }


def test_declaration(
    blocking_connection_mock, connection_mock, channel_mock,
):
    """Test queue declared and bound."""
    routing_keys = [routing_key]

    consumer = BaseConsumer(queue_name, MagicMock())
    consumer.start_consuming(exchange_name, routing_keys)

    connection_mock.close.assert_called_once()
    assert connection_mock.is_closed

    channel_mock.close.assert_called_once()
    assert channel_mock.is_closed

    channel_mock.queue_declare.assert_called_once_with(queue_name, durable=True)
    assert channel_mock.queue_bind.call_count == len(routing_keys)
    assert channel_mock.queue_bind.call_args_list[0][0] == (queue_name, exchange_name)
    assert channel_mock.queue_bind.call_args_list[0][1] == {"routing_key": routing_key}


def test_declaration_with_multiple_binding(
    blocking_connection_mock, channel_mock, connection_mock,
):
    """Test queue declared and bound with a multiple exchanged."""
    exchange1 = "foo_exchange"
    routing_keys1 = ["foo", "bar"]
    exchange2 = "baz_exchange"
    routing_keys2 = ["baz"]
    durable = False

    with BaseConsumer(queue_name, MagicMock(), durable=durable) as consumer:
        consumer.bind(exchange1, routing_keys1)
        consumer.bind(exchange2, routing_keys2)
        consumer.start_consuming(queue_name)

    connection_mock.close.assert_called_once()
    assert connection_mock.is_closed

    channel_mock.close.assert_called_once()
    assert channel_mock.is_closed

    channel_mock.queue_declare.assert_called_once_with(queue_name, durable=durable)
    assert channel_mock.queue_bind.call_count == len(routing_keys1 + routing_keys2)

    expected_bind = {(queue_name, exchange1), (queue_name, exchange2)}
    assert expected_bind == {call[0] for call in channel_mock.queue_bind.call_args_list}
    assert set(routing_keys1 + routing_keys2) == {
        call[1]["routing_key"] for call in channel_mock.queue_bind.call_args_list
    }


def test_consumer_success_message(
    blocking_connection_mock, channel_mock, message_factory,
):
    """Test callback called with expected args and message acked then."""
    message_body = {"data": {"id": 1}}
    message_factory(message_body, routing_key)
    callback_mock = MagicMock()

    consumer = BaseConsumer(queue_name, callback_mock)
    consumer.start_consuming(exchange_name, [routing_key])

    callback_mock.assert_called_once_with(routing_key, message_body)
    channel_mock.basic_ack.assert_called_once_with(delivery_tag=BLOCKING_DELIVERY_TAG)


@pytest.mark.parametrize("requeue", [False, True])
def test_consumer_unexpect_error(
    blocking_connection_mock, channel_mock, message_factory, requeue,
):
    """
    Test message nacked with various requeue argument.

    In case of unexpected exception it raised after message processed.
    """
    message_body = {"data": {"id": 1}}
    message_factory(message_body, routing_key)
    callback_mock = MagicMock(side_effect=KeyError)

    consumer = BaseConsumer(queue_name, callback_mock, requeue_msg=requeue)

    with pytest.raises(KeyError):
        consumer.start_consuming(exchange_name, [routing_key])

    callback_mock.assert_called_once_with(routing_key, message_body)
    channel_mock.basic_nack.assert_called_once_with(
        delivery_tag=BLOCKING_DELIVERY_TAG, requeue=requeue,
    )
