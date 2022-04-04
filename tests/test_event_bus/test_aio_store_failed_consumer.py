import asyncio
import json

from aio_pika import ExchangeType
from asynctest import CoroutineMock

from toolset.event_bus.aio.consumers import BaseGarbageConsumer
from toolset.event_bus.constants import GARBAGE_QUEUE_SUFFIX, POST_RETRY_EXCHANGE_SUFFIX

EXCHANGE_NAME = "test"


class ConsumerForTest(BaseGarbageConsumer):
    """Consumer class for tests."""

    exchange_name = EXCHANGE_NAME


async def test_store_failed_consumer_declarations(  # noqa: WPS210 too many local variables
    robust_connection_mock, connection_mock, channel_mock, queue_mock,
):
    """Test queue declared and binded."""
    # main params
    durable = False
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    prefetch_count = 5
    callback = CoroutineMock()
    # expected arguments
    garbage_queue_name = f"{queue_name}.{GARBAGE_QUEUE_SUFFIX}"
    post_retry_exchange_name = f"{EXCHANGE_NAME}.{POST_RETRY_EXCHANGE_SUFFIX}"

    async with ConsumerForTest(queue_name, durable=durable) as consumer:
        await consumer.consume(callback, exchange_name, routing_keys, prefetch_count=prefetch_count)

    assert channel_mock.declare_queue.call_count == 2  # called for queue and garbage queue
    # queue declared with proper args
    queue_declaration_call = channel_mock.declare_queue.call_args_list[0]
    assert queue_declaration_call[0] == (queue_name,)
    assert queue_declaration_call[1] == {"durable": durable}
    # garbage queue declared with proper args
    garbage_queue_declaration_call = channel_mock.declare_queue.call_args_list[1]
    assert garbage_queue_declaration_call[0] == (garbage_queue_name,)
    assert garbage_queue_declaration_call[1] == {
        "durable": True,
        "arguments": {
            "x-dead-letter-exchange": post_retry_exchange_name,
            "x-dead-letter-routing-key": queue_name,
        },
    }
    # post retry exchange declared
    channel_mock.declare_exchange.assert_called_once_with(
        name=post_retry_exchange_name, durable=True, type=ExchangeType.DIRECT,
    )

    channel_mock.set_qos.asset_called_once_with(prefetch_count)


async def test_store_failed_consumer_success_message_processing(
    robust_connection_mock, rabbit_message_factory, full_queue_factory,
):
    """Test callback called with proper args and message acked."""
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    callback = CoroutineMock()

    message_body = {"data": {"id": 1}}
    message_rk = routing_keys[0]
    message = rabbit_message_factory(message_body, message_rk)
    full_queue_factory([message])

    async with ConsumerForTest(queue_name) as consumer:
        await asyncio.create_task(consumer.consume(callback, exchange_name, routing_keys))

    callback.assert_awaited_once(message_body, message_rk)
    assert message.ack.called


async def test_store_failed_consumer_unexpected_error(  # noqa: WPS210 too many local variables
    robust_connection_mock, rabbit_message_factory, full_queue_factory,
):
    """Test message acked and republished (moved to garbage)."""
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    callback = CoroutineMock(side_effect=KeyError)

    message_body = {"data": {"id": 1}}
    message_rk = routing_keys[0]
    message = rabbit_message_factory(message_body, message_rk)
    full_queue_factory([message])

    async with ConsumerForTest(queue_name) as consumer:
        await asyncio.create_task(consumer.consume(callback, exchange_name, routing_keys))

    callback.assert_awaited_once(message_body, message_rk)
    assert message.ack.called
    exchange_mock = consumer._post_retry_exchange  # noqa: WPS441 control variable after block
    assert exchange_mock.publish.call_count == 1

    call_args = exchange_mock.publish.call_args_list[0][0]
    garbage_message = json.loads(call_args[0].body)  # first arg - aio_pika.Message obj
    assert garbage_message == {"error": repr(KeyError()), **message_body}

    # routing key
    assert call_args[1] == consumer._garbage_queue_name  # noqa: WPS441 control variable after block
