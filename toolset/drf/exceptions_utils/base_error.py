from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status


class BaseCustomError(exceptions.APIException):
    """
    Overrides default exception with 422 error_code instead of 400.

    This is required to distinguish errors with JS client from business errors.
    We cannot override `exceptions.ValidationError` directly, because DRF ignores
    inheritance many times: https://stackoverflow.com/a/51567740
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("Invalid input.")
    default_code = "invalid"

    def __init__(self, detail=None, error_code=None) -> None:
        """Override to make handle list of errors."""
        if detail is None:
            detail = self.default_detail
        if error_code is None:
            self.error_code = self.default_code
        else:
            self.error_code = error_code

        # errors should be coerced to list
        if not isinstance(detail, (dict, list)):
            detail = [detail]

        super().__init__(detail)


class BaseProxyCustomError(BaseCustomError):
    """
    Same as BaseCustomError, but handler won't add service name into error code.

    Use it if you want to proxy errors from other services.
    """
