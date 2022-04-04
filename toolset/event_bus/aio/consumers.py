import asyncio
import json
import os
import typing as tp
from functools import partial

import aio_pika
from aio_pika import DeliveryMode, Exchange, ExchangeType
from structlog import get_logger
from typing_extensions import Protocol

from toolset.event_bus.constants import GARBAGE_QUEUE_SUFFIX, POST_RETRY_EXCHANGE_SUFFIX
from toolset.typing_helpers import JSON

logger = get_logger("toolset.event_bus.consumers")


class ProcessMessageFunctionType(Protocol):
    """Protocol for process rabbit message."""

    def __call__(self, message_body: JSON, routing_key: str, **kwargs) -> tp.Awaitable[None]:
        """Call."""


class ConsumerBaseException(Exception):
    """Consumer base exception class."""


class BaseClient:
    """
    Base client.

    Used to initialize connection with message broker.
    """

    host: str = os.environ.get("RABBITMQ_HOST", "localhost")
    port: int = int(os.environ.get("RABBITMQ_PORT", 5672))
    user: str = os.environ.get("RABBITMQ_USER", "guest")
    password: str = os.environ.get("RABBITMQ_PASSWORD", "guest")

    connection: tp.Optional[aio_pika.RobustConnection]
    channel: tp.Optional[aio_pika.Channel]

    def __init__(self) -> None:
        """Init."""
        self.connection = None
        self.channel = None

    async def __aenter__(self):
        """Create connection."""
        await self.init_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close connection."""
        await self.close_connection()

    async def init_connection(self) -> None:
        """Init connection and channel if they doesn't exist or closed."""
        if not self.connection or self.connection.is_closed:
            self.connection = await self._get_connection()
            logger.debug("Connection established")
        else:
            logger.debug("Connection already open")

        if not self.channel or self.channel.is_closed:
            self.channel = await self.connection.channel()
            logger.debug("Channel established")
        else:
            logger.debug("Channel already open")

    async def close_connection(self) -> None:
        """Close channel and connection."""
        if self.channel:
            await self.channel.close()  # type: ignore # untyped method .close()
        if self.connection:
            await self.connection.close()  # type: ignore # untyped method .close()
        logger.debug("Connection closed")

    async def _get_connection(self) -> aio_pika.RobustConnection:
        """Get rabbitmq connection."""
        return await aio_pika.connect_robust(
            host=self.host, port=self.port, login=self.user, password=self.password,
        )

    def _check_setup(self) -> None:
        if not self.channel or self.channel.is_closed:
            raise RuntimeError("PubSub class is not configured")


class BaseConsumer(BaseClient):
    """
    Consumer.

    You can create consumer with custom behavior by subclassing BaseConsumer
    and reassigning methods:
    .declare_all()
    .bind_all()
    ._process_unexpected_exception()
    ._process_message()

    """

    bindings: tp.Dict[str, tp.Iterable[str]]
    queue: aio_pika.Queue

    def __init__(
        self, queue_name: str, durable: bool = True, requeue_msg: bool = True, delay: int = 0,
    ):
        """
        Define consumer params.

        Parameters:
            queue_name: name of the main consumer's queue
            durable: if set to True - queue survive broker restart
            requeue_msg: send message back to queue if consumer close unexpectedly
            delay: delay in seconds before processing unexpected exception

        It is prohibited to change params of existing queue.
        Queue params: durable.

        """
        super().__init__()
        self._durable = durable
        self._requeue_msg = requeue_msg
        self._queue_name = queue_name
        self._delay = delay
        self.bindings = {}

    def bind(self, exchange_name: str, routing_keys: tp.Iterable[str]):
        """
        Add queue binding data.

        Parameters:
            exchange_name: name of the exchange that will be binded with queue
            routing_keys: routing keys to bing queue with exchange

        """
        self.bindings[exchange_name] = routing_keys

    async def consume(
        self,
        callback: ProcessMessageFunctionType,
        exchange_name: tp.Optional[str] = None,
        routing_keys: tp.Optional[tp.Iterable[str]] = None,
        prefetch_count: int = 10,
        **context,
    ):
        """
        Make all declarations and start consuming.

        Parameters:
            callback: function for processing received message
            prefetch_count: number of unacknowledged messages per channel
            exchange_name: name of the exchange that will be binded with queue
            routing_keys: routing keys to bing queue with exchange

        If you need to bind queue with several exchanges use method .bind()
        If you need to provide extra context to callback (app, dp_pool, etc..),
        provide it as kwargs.

        """
        if exchange_name and routing_keys:
            self.bind(exchange_name, routing_keys)

        self._check_setup()
        await self.channel.set_qos(prefetch_count=prefetch_count)  # type: ignore

        await self.declare_all()
        await self.bind_all()
        await self._listen_queue(callback, context)

    async def declare_all(self) -> None:
        """Make all declarations and bindings."""
        await self.declare_main_queue()

    async def declare_main_queue(self) -> None:
        """Declare main queue."""
        self.queue = await self.channel.declare_queue(  # type: ignore
            self._queue_name, durable=self._durable,
        )

    async def bind_all(self) -> None:
        """Make all bindings."""
        await self._bind_main_queue()

    async def _bind_main_queue(self) -> None:
        if not self.bindings:
            raise ConsumerBaseException("At least one binding should be registered")
        for exchange_name, routing_keys in self.bindings.items():
            await self._bind_queue(self.queue, exchange_name, routing_keys)

    async def _listen_queue(self, callback: ProcessMessageFunctionType, context):
        """Run consumer and get messages from queue."""
        async with self.queue.iterator() as queue_iter:
            message: aio_pika.IncomingMessage
            async for message in queue_iter:
                asyncio.create_task(self._process_message(message, callback, context))

    async def _bind_queue(
        self, queue: aio_pika.Queue, exchange_name, routing_keys: tp.Iterable[str],
    ) -> None:
        tasks = [queue.bind(exchange_name, routing_key=routing_key) for routing_key in routing_keys]
        await asyncio.gather(*tasks)

    async def _process_message(
        self, message: aio_pika.IncomingMessage, callback: ProcessMessageFunctionType, context,
    ) -> None:

        async with message.process(ignore_processed=True):

            try:
                message_body = json.loads(message.body)
            except json.decoder.JSONDecodeError:
                logger.error("Message decoding failed")
                message.ack()
                return

            try:
                await callback(message_body, message.routing_key, **context)

            except Exception as exc:
                logger.error("Couldn't process message", exc=str(exc))
                await self._process_unexpected_exception(message, exc)
                return

            message.ack()

    async def _process_unexpected_exception(
        self, message: aio_pika.IncomingMessage, exc: Exception,
    ):
        await asyncio.sleep(self._delay)
        message.nack(requeue=self._requeue_msg)


class BaseGarbageConsumer(BaseConsumer):  # noqa: WPS214 too many methods
    """
    Consumer that stores failed messages in garbage queue.

    How does it works:
    During message processing if handler (callback) exits with exception,
    message body will be republished to garbage queue and stored there until
    it will be deleted (acked) or rejected (nack with requeue=False).

    If message rejected from garbage queue it goes back to the original queue
    for reprocessing.

    """

    exchange_name: str
    _garbage_queue_name: str
    garbage_queue: aio_pika.Queue
    _post_retry_exchange_name: str
    _post_retry_exchange: Exchange

    def __init__(self, queue_name: str, **kwargs) -> None:
        """Define name for post retry exchange."""
        self._garbage_queue_name = f"{queue_name}.{GARBAGE_QUEUE_SUFFIX}"
        self._post_retry_exchange_name: str = f"{self.exchange_name}.{POST_RETRY_EXCHANGE_SUFFIX}"
        super().__init__(queue_name, **kwargs)

    async def declare_all(self) -> None:
        """Declare post retry exchange, declare and bind main queue and garbage queue."""
        await self._declare_post_retry_exchange()
        await self.declare_main_queue()
        await self.declare_garbage_queue()

    async def bind_all(self) -> None:
        """Make all bindings."""
        await self._bind_main_queue()
        await self._bind_garbage_queue()
        # bind queue to post retry exchange to be able to receive messages from garbage queue
        await self._bind_queue(self.queue, self._post_retry_exchange_name, [self._queue_name])

    async def declare_garbage_queue(self) -> None:
        """Declare garbage queue."""
        self.garbage_queue = await self.channel.declare_queue(  # type: ignore
            self._garbage_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self._post_retry_exchange_name,
                "x-dead-letter-routing-key": self._queue_name,
            },
        )

    async def _bind_garbage_queue(self) -> None:
        await self._bind_queue(
            self.garbage_queue, self._post_retry_exchange_name, [self._garbage_queue_name],
        )

    async def _declare_post_retry_exchange(self) -> None:
        self._post_retry_exchange = await self.channel.declare_exchange(  # type: ignore
            name=self._post_retry_exchange_name, type=ExchangeType.DIRECT, durable=True,
        )

    async def _process_unexpected_exception(
        self, message: aio_pika.IncomingMessage, exc: Exception,
    ) -> None:
        await self._move_to_garbage_queue(message, exc)
        message.ack()

    async def _move_to_garbage_queue(
        self, message: aio_pika.IncomingMessage, exc: Exception,
    ) -> None:
        self._check_setup()
        exchange: Exchange = self._post_retry_exchange

        body = json.loads(message.body)
        body["error"] = repr(exc)
        body_bytes = json.dumps(body).encode()

        await exchange.publish(
            aio_pika.Message(body_bytes, delivery_mode=DeliveryMode.PERSISTENT),
            self._garbage_queue_name,
        )
        logger.info("Message moved to garbage queue")
