import asyncio
import typing as tp
from functools import wraps
from time import sleep

from toolset.typing_helpers import ASYNC_FUNC, FUNC_RESULT, TFunc


def retry(  # noqa: WPS231 Found too high function cognitive complexity
    *exceptions: tp.Type[Exception],
    attempts: int = 3,
    wait_time_seconds: float = 0.5,
    backoff: int = 2,
) -> tp.Callable[[TFunc], TFunc]:
    """Try to call a func `attempts` times with `wait_time_seconds` breaks multiplied each time by `backoff`."""

    def _retry(func: TFunc) -> TFunc:
        @wraps(func)
        def _inner(*args, **kwargs) -> FUNC_RESULT:
            exception: Exception = Exception()
            wait = wait_time_seconds
            for _ in range(attempts):  # noqa: WPS122 unused variables definition
                try:
                    res: FUNC_RESULT = func(*args, **kwargs)
                except exceptions as exc:
                    exception = exc
                    sleep(wait)
                    wait *= backoff
                    continue
                break
            else:
                # raise catch exception
                raise exception
            return res

        return tp.cast(TFunc, _inner)

    return _retry


def aio_retry(  # noqa: WPS231 Found too high function cognitive complexity
    *exceptions: tp.Type[Exception],
    attempts: int = 3,
    wait_time_seconds: float = 0.5,
    backoff: int = 2,
):
    """Try to call a func `attempts` times with `wait_time_seconds` breaks multiplied each time by `backoff`."""

    def _retry(func: ASYNC_FUNC) -> ASYNC_FUNC:
        @wraps(func)
        async def _inner(*args, **kwargs) -> FUNC_RESULT:
            exception: Exception = Exception()
            wait = wait_time_seconds
            for _ in range(attempts):  # noqa: WPS122 unused variables definition
                try:
                    res = await func(*args, **kwargs)
                except exceptions as exc:
                    exception = exc
                    await asyncio.sleep(wait)
                    wait *= backoff
                    continue
                return res
            # raise catch exception
            raise exception

        return tp.cast(ASYNC_FUNC, _inner)

    return _retry
