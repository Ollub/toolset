from typing import Mapping

from django.conf import settings
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as drf_exception_handler

from toolset.drf.exceptions_utils import BaseCustomError, BaseProxyCustomError

SERVICE_NAME = settings.SERVICE_NAME.upper()
DEFAULT_EXCEPTION = f"{SERVICE_NAME}/DEFAULT_EXCEPTION"


def _custom_as_serializer_error(exc: "BaseCustomError"):
    """
    Adapted from `rest_framework.serializers.as_serializer_error`.

    Which works only for DRF's own validation errors.
    """
    detail = exc.detail

    if isinstance(detail, Mapping):
        # If errors are in a dict we use the standard {key: list of values}.
        # Here we ensure that all the values are *lists* of errors.
        return {
            key: value if isinstance(value, (list, Mapping)) else [value]
            for key, value in detail.items()
        }
    elif isinstance(detail, list):
        # Errors raised as a list are non-field errors.
        return {api_settings.NON_FIELD_ERRORS_KEY: detail}
    # Errors raised as a string are non-field errors.
    return {api_settings.NON_FIELD_ERRORS_KEY: [detail]}


def custom_exception_handler(exc, context):
    """Handle BaseCustomErrors."""
    # Calls REST framework's default exception handler first,
    # to get the standard error response.
    if isinstance(exc, BaseCustomError):
        # DRF wraps errors only for it's own validation errors. We need to do this
        # manually
        exc = exc.__class__(detail=_custom_as_serializer_error(exc), error_code=exc.error_code)

    response = drf_exception_handler(exc, context)
    # Adds the HTTP status code to the response.
    if response is not None:
        data = response.data
        response.data = {"code": response.status_code, "detail": data}
        if isinstance(exc, BaseProxyCustomError):
            # do not add service name, proxy already has error code
            response.data["error_code"] = exc.error_code
        elif isinstance(exc, BaseCustomError):
            # provide service-specific error code for client application
            response.data["error_code"] = f"{SERVICE_NAME}/{exc.error_code}"
        else:
            response.data["error_code"] = DEFAULT_EXCEPTION

    return response
