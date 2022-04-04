import json
import typing as tp

import structlog
from pika import BasicProperties, URLParameters
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from toolset.event_bus.constants import GARBAGE_QUEUE_SUFFIX, POST_RETRY_EXCHANGE_SUFFIX
from toolset.event_bus.django.base import DEFAULT_PROPERTIES, pika_parameters
from toolset.event_bus.django.consumers.base import BaseConsumer
from toolset.event_bus.django.consumers.constants import ProcessMessageFunctionType
from toolset.typing_helpers import JSON

logger = structlog.get_logger("toolset.event_bus.consumers.garbage_consumer")


class GarbageConsumer(BaseConsumer):
    """Subscriber logic for Rabbit with dlx exchange and garbage queue.

    Retry logic not implemented yet (only garbage queue is available).

    How does it works:
    1. If param store_failed set to True:
    During message processing if handler (callback) exits with exception
    message body will be republished to garbage queue and stored there until
    it will be deleted (acked) or rejected (nack with requeue=False).

    If message rejected from garbage queue it goes back to the original queue
    for reprocessing.

    2. If param store_failed set to False:
    In message handler exists with exception,
    message will be deleted if param `requeue_msg` set to False
    or returned to queue if it set to True.
    """

    main_exchange_name: str

    def __init__(
        self,
        queue_name: str,
        callback: ProcessMessageFunctionType,
        url_params: URLParameters = pika_parameters,
        pika_props: BasicProperties = DEFAULT_PROPERTIES,
        prefetch_count: int = 10,
        store_failed: bool = False,
        requeue_msg: bool = True,
        durable: bool = True,
    ):
        """Define DLX consumer params.

        @param queue_name: Name of queue
        @param callback: Function with args: routing_keys (str) and message body (as JSON dict)
        @param url_params: Connect to RabbitMQ via an AMQP URL in the format:
        @param pika_props: Connection properties
        @param prefetch_count: number of unacknowledged messages per channel
        @param store_failed: send to garbage queue unprocessed messages
        @param requeue_msg: send message back to queue if consumer close unexpectedly
        @param durable: Survive reboots of the broker
        """
        super().__init__(
            queue_name,
            callback,
            url_params,
            pika_props,
            prefetch_count,
            requeue_msg=requeue_msg,
            durable=durable,
        )

        self._queue_name = queue_name
        self._garbage_queue_name = f"{queue_name}.{GARBAGE_QUEUE_SUFFIX}"
        self._store_failed_msg = store_failed

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

        # Declare main queue
        self._declare_main_queue(channel)
        self._declare_and_bind_queue(channel)

        if self._store_failed_msg:
            self._declare_garbage_queue_and_exchange(channel)

        channel.basic_consume(
            queue=self._queue_name, on_message_callback=self._pika_callback,
        )

        try:
            channel.start_consuming()

        except Exception as exc:
            logger.exception(exc)
            raise

        finally:
            if not self._in_ctx:
                channel.close()
                connection.close()

    @property
    def _post_retry_exchange_name(self) -> str:
        return f"{self.main_exchange_name}.{POST_RETRY_EXCHANGE_SUFFIX}"

    def _declare_garbage_queue_and_exchange(self, ch: BlockingChannel) -> None:
        """Declare a retry exchange and garbage queue."""
        ch.exchange_declare(
            self._post_retry_exchange_name, exchange_type="direct", durable=True,
        )

        # Declare garbage queue
        ch.queue_declare(
            self._garbage_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self._post_retry_exchange_name,
                "x-dead-letter-routing-key": self._queue_name,
            },
        )

        # Bind the garbage queue to the retry exchange
        self._bind_queue(
            ch,
            self._garbage_queue_name,
            self._post_retry_exchange_name,
            [self._garbage_queue_name],
        )

        # Bind the main queue to retry exchange
        self._bind_queue(ch, self._queue_name, self._post_retry_exchange_name, [self._queue_name])

    def _process_unexpected_exception(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
        exception: Exception,
    ) -> None:

        if self._store_failed_msg:

            self._move_to_garbage_queue(ch, body, exception)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:

            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=self._requeue_msg)

    def _move_to_garbage_queue(self, ch: BlockingChannel, body: bytes, exc: Exception) -> None:
        """Move message to the garbage queue."""
        payload = json.loads(body)
        payload["error"] = repr(exc)
        body_bytes = json.dumps(payload).encode()

        ch.basic_publish(
            exchange=self._post_retry_exchange_name,
            routing_key=self._garbage_queue_name,
            body=body_bytes,
        )

        logger.info("Message moved to garbage queue")
