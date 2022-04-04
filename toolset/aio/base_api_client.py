import os
import typing as tp
from collections.abc import Iterable

from aiohttp import ClientResponse, ClientSession
from aiohttp.typedefs import StrOrURL

from toolset.typing_helpers import JSON_DICT, JSON_MAPPING

OPTIONAL_JSON_MAPPING = tp.Optional[JSON_MAPPING]
PARAMS_TYPE = tp.Tuple[str, tp.Union[str, int]]


class BaseApiClient:
    """Base api client."""

    service_token: tp.Optional[str] = os.environ.get("SERVICE_SECRET")
    service_name: str

    default_timeout = 120

    def __init__(self):
        """Init."""
        self.session = ClientSession()
        self.secret_headers = {"X-SERVICE-SECRET": f"{self.service_token}:{self.service_name}"}

    async def close(self):
        """Close session."""
        await self.session.close()

    def make_params(self, params: JSON_DICT) -> tp.List[PARAMS_TYPE]:
        """Make params for request from dict to tuple-like list."""
        params_list: tp.List[PARAMS_TYPE] = []
        for param_name, param_value in params.items():
            if not isinstance(param_value, (str, bytes)) and isinstance(param_value, Iterable):
                params_list.extend((param_name, str(single_value)) for single_value in param_value)
            elif isinstance(param_value, int):
                params_list.append((param_name, str(param_value)))
            else:
                params_list.append((param_name, param_value))  # type: ignore
        return params_list

    @property
    def patched_headers(self) -> JSON_MAPPING:
        """Headers with dd span context."""
        headers = {**self.secret_headers}
        return headers

    async def get(self, url: StrOrURL, allow_redirects: bool = True, **kwargs) -> ClientResponse:
        """Get."""
        kwargs = self._update_kwargs(**kwargs)
        return await self.session.get(
            url, allow_redirects=allow_redirects, **{"timeout": self.default_timeout, **kwargs},
        )

    async def post(
        self,
        url: StrOrURL,
        data: OPTIONAL_JSON_MAPPING = None,
        json: OPTIONAL_JSON_MAPPING = None,
        **kwargs,
    ) -> ClientResponse:
        """Post."""
        kwargs = self._update_kwargs(**kwargs)
        return await self.session.post(
            url, data=data, json=json, **{"timeout": self.default_timeout, **kwargs},
        )

    async def patch(
        self, url: StrOrURL, data: OPTIONAL_JSON_MAPPING = None, **kwargs,
    ) -> ClientResponse:
        """Patch."""
        kwargs = self._update_kwargs(**kwargs)
        return await self.session.patch(
            url, data=data, **{"timeout": self.default_timeout, **kwargs},
        )

    async def put(
        self, url: StrOrURL, data: OPTIONAL_JSON_MAPPING = None, **kwargs,
    ) -> ClientResponse:
        """Put."""
        kwargs = self._update_kwargs(**kwargs)
        return await self.session.put(url, data=data, **{"timeout": self.default_timeout, **kwargs})

    async def delete(self, url: StrOrURL, **kwargs) -> ClientResponse:
        """Delete."""
        kwargs = self._update_kwargs(**kwargs)
        return await self.session.delete(url, **{"timeout": self.default_timeout, **kwargs})

    def _update_kwargs(self, **kwargs) -> JSON_DICT:
        """
        Update kwargs to request.

        1. Inject dd and security headers.
        """
        kwargs["headers"] = {**self.patched_headers, **kwargs.get("headers", {})}
        return kwargs
