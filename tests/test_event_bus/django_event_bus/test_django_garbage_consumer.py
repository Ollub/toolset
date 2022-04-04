import json
from unittest.mock import MagicMock

from toolset.event_bus.constants import GARBAGE_QUEUE_SUFFIX, POST_RETRY_EXCHANGE_SUFFIX
from toolset.event_bus.django import GarbageConsumer
from tests.test_event_bus.django_event_bus.conftest import BLOCKING_DELIVERY_TAG

EXCHANGE_NAME = "test"


class GarbageConsumerForTest(GarbageConsumer):
    """Test garbage consumer."""

    main_exchange_name = EXCHANGE_NAME


def test_store_failed_consumer(  # noqa: WPS210 Found too many local variables
    blocking_connection_mock, connection_mock, channel_mock,
):
    """Test garbage consumer configured correctly."""
    durable = True
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    prefetch_count = 5
    callback = MagicMock()

    garbage_queue_name = f"{queue_name}.{GARBAGE_QUEUE_SUFFIX}"
    post_retry_exchange_name = f"{EXCHANGE_NAME}.{POST_RETRY_EXCHANGE_SUFFIX}"

    consumer = GarbageConsumerForTest(
        queue_name, callback, store_failed=True, prefetch_count=prefetch_count,
    )
    consumer.start_consuming(exchange_name, routing_keys)

    queue_declaration_call = channel_mock.queue_declare.call_args_list[0]

    assert queue_declaration_call[0][0] == queue_name
    assert queue_declaration_call[1] == {"durable": durable}

    garbage_queue_declaration_call = channel_mock.queue_declare.call_args_list[1]
    assert garbage_queue_declaration_call[0][0] == garbage_queue_name
    assert garbage_queue_declaration_call[1] == {
        "durable": durable,
        "arguments": {
            "x-dead-letter-exchange": post_retry_exchange_name,
            "x-dead-letter-routing-key": queue_name,
        },
    }

    channel_mock.exchange_declare.assert_called_once_with(
        post_retry_exchange_name, exchange_type="direct", durable=durable,
    )


def test_consumer_process_message_successfully(
    blocking_connection_mock, channel_mock, message_factory,
):
    """Test callback called and message processed successfully."""
    message_body = {"data": {"id": 1}}
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    prefetch_count = 5
    callback = MagicMock()

    message_factory(message_body, routing_keys[0])

    consumer = GarbageConsumerForTest(
        queue_name, callback, store_failed=True, prefetch_count=prefetch_count,
    )
    consumer.start_consuming(exchange_name, routing_keys)

    callback.assert_called_once_with(routing_keys[0], message_body)
    channel_mock.basic_ack.assert_called_once_with(delivery_tag=BLOCKING_DELIVERY_TAG)


def test_consumer_process_and_move_to_garbage(
    blocking_connection_mock, channel_mock, message_factory,
):
    """Test message processing failed and message moved to garbage queue."""
    message_body = {"data": {"id": 1}}
    queue_name = "test_queue"
    routing_keys = ["foo", "bar"]
    callback = MagicMock(side_effect=KeyError)

    garbage_queue_name = f"{queue_name}.{GARBAGE_QUEUE_SUFFIX}"
    post_retry_exchange_name = f"{EXCHANGE_NAME}.{POST_RETRY_EXCHANGE_SUFFIX}"

    message_factory(message_body, routing_keys[0])

    consumer = GarbageConsumerForTest(queue_name, callback, store_failed=True)
    consumer.start_consuming("test_exchange", routing_keys)

    callback.assert_called_once_with(routing_keys[0], message_body)
    channel_mock.basic_ack.assert_called_once_with(delivery_tag=BLOCKING_DELIVERY_TAG)

    garbage_message = {**message_body, "error": repr(KeyError())}
    channel_mock.basic_publish.assert_called_once_with(
        exchange=post_retry_exchange_name,
        routing_key=garbage_queue_name,
        body=json.dumps(garbage_message).encode(),
    )
