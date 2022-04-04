import json
import typing as tp

import structlog
from pika import BasicProperties, URLParameters
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.spec import Basic

from toolset.event_bus.django.base import DEFAULT_PROPERTIES, BaseMessageBus, pika_parameters
from toolset.event_bus.django.consumers.constants import (
    CONSUMER_CONNECTION_PREFETCH_COUNT,
    ConsumerBaseException,
    ProcessMessageFunctionType,
)
from toolset.typing_helpers import JSON

logger = structlog.get_logger("toolset.event_bus.consumers.base")


class BaseConsumer(BaseMessageBus):
    """Base logic for consumer."""

    bindings: tp.Dict[str, tp.Iterable[str]]

    def __init__(
        self,
        queue_name: str,
        callback: ProcessMessageFunctionType,
        url_params: URLParameters = pika_parameters,
        pika_props: BasicProperties = DEFAULT_PROPERTIES,
        prefetch_count: int = CONSUMER_CONNECTION_PREFETCH_COUNT,
        requeue_msg: bool = True,
        durable: bool = True,
    ):
        """Define base consumer.

        @param queue_name: name of the main consumer's queue
        @param callback: function with args: routing_keys (str) and message body (as JSON dict)
        @param url_params: Connect to RabbitMQ via an AMQP URL in the format:
        @param pika_props: Connection properties
        @param prefetch_count: number of unacknowledged messages per channel
        @param requeue_msg: send message back to queue if consumer close unexpectedly
        @param durable: Survive reboots of the broker
        """
        super().__init__(url_params, pika_props)
        self._queue_name = queue_name

        self.bindings = {}
        self.callback = callback
        self._prefetch_count = prefetch_count
        self._requeue_msg = requeue_msg
        self._durable = durable

    def start_consuming(
        self,
        exchange_name: tp.Optional[str] = None,
        routing_keys: tp.Optional[tp.Iterable[str]] = None,
    ):
        """Register and run consumer.

        @param exchange_name: name of the exchange that will be bind with queue
        @param routing_keys: routing keys to bind queue with exchange
        """
        connection = self._get_connection()
        channel = self._get_channel(connection)

        if exchange_name and routing_keys:
            self.bind(exchange_name, routing_keys)

        self._declare_main_queue(channel)
        self._declare_and_bind_queue(channel)
        logger.debug(
            "Declared a new queue to consuming",
            exchange_name=exchange_name,
            queue_name=self._queue_name,
            routing_keys=routing_keys,
        )

        self._consume(channel, connection)

    def bind(self, exchange_name: str, routing_keys: tp.Iterable[str]):
        """
        Add queue binding data.

        Parameters:
            exchange_name: name of the exchange that will be binded with queue
            routing_keys: routing keys to bing queue with exchange

        """
        self.bindings[exchange_name] = routing_keys

    def _consume(self, channel: BlockingChannel, connection: BlockingConnection):
        channel.basic_consume(
            queue=self._queue_name, on_message_callback=self._pika_callback,
        )

        logger.debug("Start consuming")
        try:
            channel.start_consuming()
        except Exception as exc:
            logger.exception(exc)
            raise

        finally:
            if not self._in_ctx:
                if channel.is_open:
                    channel.close()
                if connection.is_open:
                    connection.close()

                logger.debug("Channel & connection closed (without ctx)")

    def _get_channel(self, connection: tp.Optional[BlockingConnection] = None) -> BlockingChannel:
        """Init a new instance of BlockingChannel."""
        channel = super()._get_channel(connection)
        channel.basic_qos(prefetch_count=self._prefetch_count)

        logger.debug(
            "Created a new channel with prefetch_count", prefetch_count=self._prefetch_count,
        )

        return channel

    def _bind_queue(
        self,
        ch: BlockingChannel,
        queue_name: str,
        exchange_name: str,
        routing_keys: tp.Iterable[str],
    ) -> None:
        """Bing queue for each routing key."""
        for routing_key in routing_keys:
            ch.queue_bind(queue_name, exchange_name, routing_key=routing_key)

    def _declare_main_queue(self, ch: BlockingChannel):
        """Declare main queue."""
        ch.queue_declare(self._queue_name, durable=self._durable)

    def _declare_and_bind_queue(self, ch: BlockingChannel):
        """Declare and bind the queue."""
        if not self.bindings:
            raise ConsumerBaseException("At least one binding should be registered")

        for exchange_name, routing_keys in self.bindings.items():
            self._bind_queue(ch, self._queue_name, exchange_name, routing_keys)

    def _pika_callback(
        self, ch: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body,
    ):
        """Process incoming message.

        Here we are going to:
            - Decode json from the message body
            - Takes routing key
            - Invoke callback
            - Process unexpected exceptions if it was discovered
        """
        logger.debug("Received a new message", body=body)

        try:
            payload = json.loads(body)

        except json.decoder.JSONDecodeError:
            logger.error("Message decoding failed. Skip message (Ack).")
            ch.basic_ack(delivery_tag=method.delivery_tag)

            return

        logger.debug("Invoke callback", routing_key=method.routing_key, payload=payload)
        try:
            self.callback(method.routing_key, payload)
        except Exception as exc:
            logger.error("Couldn't process message", exc=str(exc))
            self._process_unexpected_exception(ch, method, properties, body, exc)

            return

        # Ack message if it was processed successfully
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.debug(
            "Message processed successfully, Ack", routing_key=method.routing_key, payload=payload,
        )

    def _process_unexpected_exception(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
        exception: Exception,
    ):
        """Process exception."""
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=self._requeue_msg)
        raise exception
