import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    ("exception_type", "code", "detail", "error_code"),
    [
        (
            "simple_exception",
            422,
            {"non_field_errors": ["You shall not pass!"]},
            "TEST_SERVICE/SOME_ERROR",
        ),
        (
            "default_exception",
            500,
            {"detail": "A server error occurred."},
            "TEST_SERVICE/DEFAULT_EXCEPTION",
        ),
        (
            "exception_with_mapping",
            422,
            {"detail1": ["some detail"], "detail2": ["some other detail"]},
            "TEST_SERVICE/SOME_ERROR",
        ),
        (
            "exception_from_other_service",
            422,
            {"non_field_errors": ["You shall not pass from bg!"]},
            "BG/SOME_ERROR",
        ),
    ],
)
def test_simple_exception(client, exception_type, code, detail, error_code):
    """Test toolset.drf.exceptions_utils.handlers.custom_exception_handler."""
    resp = client.post(f'{reverse("test_exceptions")}?exception_type={exception_type}')
    resp = resp.json()
    assert resp["code"] == code
    assert resp["detail"] == detail
    assert resp["error_code"] == error_code
