import typing as tp

JSON_DICT = tp.Dict[str, tp.Any]  # type: ignore
JSON_MAPPING = tp.Mapping[str, tp.Any]  # type: ignore
JSON = tp.Union[
    JSON_DICT, JSON_MAPPING, str, int, tp.List[tp.Union[str, int, JSON_DICT, JSON_MAPPING]],
]
OPTIONAL_JSON = tp.Optional[JSON]

ANY_DICT = tp.Dict[str, tp.Any]  # type: ignore

_async_func = tp.Callable[..., tp.Awaitable[tp.Any]]  # type: ignore
ASYNC_FUNC = tp.TypeVar("ASYNC_FUNC", bound=_async_func)

FUNC_RESULT = tp.TypeVar("FUNC_RESULT")
FUNC = tp.Callable[..., FUNC_RESULT]  # type: ignore
TFunc = tp.TypeVar("TFunc", bound=FUNC)  # type: ignore
