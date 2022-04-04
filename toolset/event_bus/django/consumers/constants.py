import typing_extensions as te

from toolset.typing_helpers import JSON

CONSUMER_CONNECTION_PREFETCH_COUNT = 10


class ProcessMessageFunctionType(te.Protocol):
    """Protocol for process rabbit message."""

    def __call__(self, routing_key: str, message_body: JSON) -> None:
        """Call."""


class ConsumerBaseException(Exception):
    """Consumer base exception class."""
