import pika
from structlog.testing import capture_logs

from toolset.event_bus.django.producers import DEFAULT_PROPERTIES, BaseProducer, ConnectionMock

event = {"user_id": 1}

pika.BlockingConnection = ConnectionMock


class Producer(BaseProducer):
    """Test producer."""

    exchange = "some_exchange"

    user_updated = "user_updated"


def test_simple_publish():
    """Test simple producer publish."""
    producer = Producer()
    with capture_logs() as cap_logs:
        producer.publish(producer.user_updated, event)
        assert cap_logs[0] == {
            "log_level": "info",
            "event": "Publish called",
            "args": ("toolset", "user_updated", b'{"user_id": 1}', DEFAULT_PROPERTIES),
            "kwargs": {},
        }
    producer.close()


def test_publish_in_ctx():
    """Test producer publish in ctx."""
    with Producer() as producer, capture_logs() as cap_logs:
        producer.publish(producer.user_updated, event)
        assert cap_logs[0] == {
            "log_level": "info",
            "event": "Publish called",
            "args": ("toolset", "user_updated", b'{"user_id": 1}', DEFAULT_PROPERTIES),
            "kwargs": {},
        }
