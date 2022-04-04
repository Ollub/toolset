import pytest
from aiohttp import ClientConnectorError
from aiohttp.client_reqrep import ConnectionKey

from toolset.decorators import aio_retry, retry
from toolset.drf.exceptions_utils import BaseCustomError


class CustomException(BaseCustomError):
    """Exception to test handling of our custom exception."""

    default_code = "SOME_ERROR"
    default_detail = "You shall not pass!"


@pytest.mark.parametrize(
    ("expect_exceptions", "raise_exception"),
    [
        ((ValueError, AttributeError), ValueError),
        ((ValueError,), ValueError),
        ((BaseCustomError,), CustomException),
    ],
)
def test_retry(mocker, expect_exceptions, raise_exception):
    """
    Test retry decorator.

    Tests that 'retry' decorator does retry to execute given function given number
    of attempts and raises given error afterward.
    """
    mock = mocker.Mock()
    attempts = 5

    @retry(*expect_exceptions, attempts=attempts, wait_time_seconds=0.01, backoff=2)
    def dummy_func():
        mock()
        raise raise_exception

    with pytest.raises(raise_exception):
        dummy_func()

    assert mock.call_count == attempts


@pytest.mark.parametrize(
    ("expect_exceptions", "raise_exception"),
    [((ValueError, AttributeError), ValueError), ((ValueError,), ValueError)],
)
async def test_aio_retry(mocker, expect_exceptions, raise_exception):
    """
    Test aio_retry decorator.

    Tests that 'aio_retry' decorator does retry to execute given function given number
    of attempts and raises given error afterward.
    """
    mock = mocker.Mock()
    attempts = 5

    @aio_retry(
        *expect_exceptions,
        attempts=attempts,
        wait_time_seconds=0.01,  # noqa: WPS432 magic number
        backoff=2,
    )
    async def dummy_func():
        mock()
        raise raise_exception

    with pytest.raises(raise_exception):
        await dummy_func()

    assert mock.call_count == attempts


async def test_aio_retry_with_client_connection_failed(mocker):
    """
    Test aio_retry decorator with ClientConnectorError.

    The same as "test_aio_retry", but since ClientConnectorError has to take two mandatory
    arguments when raised and this breaks ability to test it with pytest.mark.parametrize with
    other exceptions, I had to write another similar-but-not test

    """
    mock = mocker.Mock()
    attempts = 5

    @aio_retry(
        ClientConnectorError,
        attempts=attempts,
        wait_time_seconds=0.01,  # noqa: WPS432 magic number
        backoff=2,
    )
    async def dummy_func():
        mock()
        dummy_args = "host", 0, False, None, None, None, None
        raise ClientConnectorError(ConnectionKey(*dummy_args), OSError())

    with pytest.raises(ClientConnectorError):
        await dummy_func()

    assert mock.call_count == attempts
