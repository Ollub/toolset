from toolset.drf.exceptions_utils import BaseCustomError, BaseProxyCustomError


class ExceptionWithMapping(BaseCustomError):
    """Exception to test default_detail as a mapping."""

    default_detail = {"detail1": "some detail", "detail2": "some other detail"}
    default_code = "SOME_ERROR"


class CustomException(BaseCustomError):
    """Exception to test handling of our custom exception."""

    default_code = "SOME_ERROR"
    default_detail = "You shall not pass!"


class FromOtherServiceException(BaseProxyCustomError):
    """Exception to test handling of our custom exception."""

    default_code = "BG/SOME_ERROR"
    default_detail = "You shall not pass from bg!"
