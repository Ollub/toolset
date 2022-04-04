import pytest

from toolset.aio.base_api_client import BaseApiClient


class TestApiClient(BaseApiClient):
    """Test api client."""

    service_name = "test"


@pytest.mark.parametrize(
    ("input_params", "output_params"),
    [
        ({"no-pagination": "true"}, [("no-pagination", "true")]),
        ({"limit": 1, "offset": 100}, [("limit", "1"), ("offset", "100")]),
        ({"limit": 1, "user_id": [1, 2]}, [("limit", "1"), ("user_id", "1"), ("user_id", "2")]),
        ({"limit": 1, "user_id": ["1", "2"]}, [("limit", "1"), ("user_id", "1"), ("user_id", "2")]),
    ],
)
async def test_aiohttp_param(input_params, output_params):
    """Test aiohttp params from dict."""
    assert TestApiClient().make_params(input_params) == output_params
