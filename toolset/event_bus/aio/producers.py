import json

import aio_pika
import structlog
from aio_pika.pool import Pool

from toolset.typing_helpers import JSON

logger = structlog.get_logger("toolset.event_bus.producers")
DEFAULT_TIMEOUT = 60


async def get_rabbit_channel_pool(
    pool: Pool[aio_pika.Connection], max_size: int = 10,
) -> Pool[aio_pika.Channel]:
    """Get rabbit channel pool."""

    async def get_rabbit_channel() -> aio_pika.Channel:
        """Get rabbit channel."""
        connection: aio_pika.Connection
        async with pool.acquire() as connection:
            return await connection.channel()

    return Pool(get_rabbit_channel, max_size=max_size)


async def get_rabbit_connection_pool(
    host: str, port: int, user: str, password: str, max_size: int = 2,
) -> Pool[aio_pika.Connection]:
    """Get rabbit connection pool."""

    async def get_rabbit_connection() -> aio_pika.RobustConnection:
        """Get rabbit connection."""
        return await aio_pika.connect_robust(host=host, port=port, login=user, password=password)

    return Pool(get_rabbit_connection, max_size=max_size)


class BaseProducer:
    """Class to work with rabbitmq."""

    exchange_name: str

    _exchange: aio_pika.Exchange

    def __init__(
        self,
        connection_pool: Pool[aio_pika.Connection],
        channel_pool: Pool[aio_pika.Channel],
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """Init."""
        self._connection_pool = connection_pool
        self._channel_pool = channel_pool
        self.timeout = timeout

    async def get_exchange(self, channel: aio_pika.Channel) -> aio_pika.Exchange:
        """Get exchange (declare if needed)."""
        return await channel.declare_exchange(
            self.exchange_name, type=aio_pika.ExchangeType.TOPIC, durable=True,
        )

    async def teardown(self) -> None:
        """Close pools."""
        await self._channel_pool.close()  # type: ignore
        await self._connection_pool.close()  # type: ignore

    async def publish(self, routing_key: str, data: JSON) -> None:
        """Publish data to rabbit."""
        channel: aio_pika.Channel
        async with self._channel_pool.acquire() as channel:
            exchange = await self.get_exchange(channel)
            await exchange.publish(
                aio_pika.Message(json.dumps(data).encode()), routing_key, timeout=self.timeout,
            )


class BaseProducerMock:
    """Base Producer Mock."""

    def __init__(self, *args, **kwargs):
        """Init mock."""

    async def publish(self, *args, **kwargs) -> None:
        """Publish data to rabbit."""
        logger.info("Publish called", args=args, kwargs=kwargs)
