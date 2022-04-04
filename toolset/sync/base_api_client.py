import os
import typing as tp

import requests

from toolset.typing_helpers import JSON_MAPPING

OPTIONAL_JSON_MAPPING = tp.Optional[JSON_MAPPING]
DATA_TYPE = tp.Union[  # type: ignore
    None,
    str,
    bytes,
    tp.MutableMapping[str, tp.Any],
    tp.MutableMapping[str, tp.Any],
    tp.Iterable[tp.Tuple[str, tp.Optional[str]]],
    tp.IO[tp.Any],
]


class BaseApiClient:
    """Base api client."""

    service_token: tp.Optional[str] = os.environ.get("SERVICE_SECRET")
    service_name: str

    default_timeout = 120

    def __init__(self):
        """Init."""
        self.session = requests.Session()
        self.session.headers.update(
            {"X-SERVICE-SECRET": f"{self.service_token}:{self.service_name}"},
        )

    def get(self, url: str, **kwargs) -> requests.Response:
        """Get."""
        return self.session.get(url, **{"timeout": self.default_timeout, **kwargs})

    def post(
        self, url: str, data: DATA_TYPE = None, json: OPTIONAL_JSON_MAPPING = None, **kwargs,
    ) -> requests.Response:
        """Post."""
        return self.session.post(
            url, data=data, json=json, **{"timeout": self.default_timeout, **kwargs},
        )

    def patch(self, url: str, data: DATA_TYPE = None, **kwargs) -> requests.Response:
        """Patch."""
        return self.session.patch(url, data=data, **{"timeout": self.default_timeout, **kwargs})

    def put(self, url: str, data: DATA_TYPE = None, **kwargs) -> requests.Response:
        """Put."""
        return self.session.put(url, data=data, **{"timeout": self.default_timeout, **kwargs})

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Delete."""
        return self.session.delete(url, **{"timeout": self.default_timeout, **kwargs})
