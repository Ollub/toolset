import asyncio
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from structlog.testing import capture_logs

from toolset.event_bus.aio.consumers import BaseClient, BaseConsumer


async def test_client_connect(robust_connection_mock, connection_mock, channel_mock):
    """Test client connected."""
    client = BaseClient()
    with capture_logs() as cap_logs:
        await client.init_connection()
        assert cap_logs[0] == {
            "log_level": "debug",
            "event": "Connection established",
        }
        assert cap_logs[1] == {
            "log_level": "debug",
            "event": "Channel established",
        }
        await client.close_connection()
        assert cap_logs[-1] == {
            "log_level": "debug",
            "event": "Connection closed",
        }


async def test_client_connect_in_ctx(robust_connection_mock, connection_mock, channel_mock):
    """Test client connected in ctx."""
    with capture_logs() as cap_logs:
        async with BaseClient() as client:
            assert cap_logs[0] == {
                "log_level": "debug",
                "event": "Connection established",
            }
            assert cap_logs[1] == {
                "log_level": "debug",
                "event": "Channel established",
            }
        assert cap_logs[-1] == {
            "log_level": "debug",
            "event": "Connection closed",
        }


async def test_base_consumer_declarations(
    robust_connection_mock, connection_mock, channel_mock, queue_mock,
):
    """Test queue declared and binded."""
    durable = False
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    prefetch_count = 5
    callback = CoroutineMock()

    async with BaseConsumer(queue_name, durable=durable) as consumer:
        await consumer.consume(callback, exchange_name, routing_keys, prefetch_count=prefetch_count)

    # check queue declared and binded
    channel_mock.declare_queue.assert_called_once_with(queue_name, durable=durable)
    assert queue_mock.bind.call_count == len(routing_keys)
    assert queue_mock.bind.call_args_list[0][0] == (exchange_name,)
    assert set(routing_keys) == {call[1]["routing_key"] for call in queue_mock.bind.call_args_list}

    channel_mock.set_qos.asset_called_once_with(prefetch_count)


async def test_base_consumer_multiple_bindings(
    robust_connection_mock, connection_mock, channel_mock, queue_mock,
):
    """Test queue binded with every provided exchange."""
    durable = False
    queue_name = "test_queue"
    exchange1 = "foo_exchange"
    routing_keys1 = ["foo", "bar"]
    exchange2 = "baz_exchange"
    routing_keys2 = ["baz"]
    callback = CoroutineMock()

    async with BaseConsumer(queue_name, durable=durable) as consumer:
        consumer.bind(exchange1, routing_keys1)
        consumer.bind(exchange2, routing_keys2)
        await consumer.consume(queue_name, callback)

    channel_mock.declare_queue.assert_called_once_with(queue_name, durable=durable)
    assert queue_mock.bind.call_count == len(routing_keys1 + routing_keys2)
    assert {exchange1, exchange2} == {call[0][0] for call in queue_mock.bind.call_args_list}
    assert set(routing_keys1 + routing_keys2) == {
        call[1]["routing_key"] for call in queue_mock.bind.call_args_list
    }


async def test_base_consumer_success_message_processing(
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

    async with BaseConsumer(queue_name) as consumer:
        await asyncio.create_task(consumer.consume(callback, exchange_name, routing_keys))

    callback.assert_awaited_once(message_body, message_rk)
    assert message.ack.called


@pytest.mark.parametrize("requeue_msg", [False, True])
async def test_base_consumer_unexpected_error(
    robust_connection_mock, rabbit_message_factory, full_queue_factory, requeue_msg,
):
    """Test message nacked with certain requeue argument."""
    queue_name = "test_queue"
    exchange_name = "test_exchange"
    routing_keys = ["foo", "bar"]
    callback = CoroutineMock(side_effect=KeyError)

    message_body = {"data": {"id": 1}}
    message_rk = routing_keys[0]
    message = rabbit_message_factory(message_body, message_rk)
    full_queue_factory([message])

    async with BaseConsumer(queue_name, requeue_msg=requeue_msg) as consumer:
        await asyncio.create_task(consumer.consume(callback, exchange_name, routing_keys))

    # in order to execute task (process message)
    await asyncio.sleep(0)

    callback.assert_awaited_once(message_body, message_rk)
    message.nack.assert_called_once_with(requeue=requeue_msg)


@pytest.mark.parametrize("requeue_msg", [False, True])
async def test_base_consumer_not_blocking(
    robust_connection_mock, rabbit_message_factory, full_queue_factory, requeue_msg,
):
    """
    Test messages processed concurently.

    We are not awaiting message processing tasks.
    That is why we do not expect that _exit() func will be called during test.
    """
    call_count = 10
    enter_ = MagicMock()
    exit_ = MagicMock()

    async def callback(*args, **kwargs):
        enter_()
        await asyncio.sleep(0.1)
        exit_()

    message_body = {"data": {"id": 1}}
    message = rabbit_message_factory(message_body, "foo")
    full_queue_factory([message for _ in range(call_count)])

    async with BaseConsumer("test_queue", requeue_msg=requeue_msg) as consumer:
        await asyncio.create_task(consumer.consume(callback, "test_exchange", ["foo", "bar"]))

    assert enter_.call_count == call_count
    assert exit_.call_count == 0
