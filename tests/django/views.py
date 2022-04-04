from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException

from tests.django.exceptions import CustomException, ExceptionWithMapping, FromOtherServiceException

exception_type_to_exception_mapping = {
    "simple_exception": CustomException,
    "default_exception": APIException,
    "exception_with_mapping": ExceptionWithMapping,
    "exception_from_other_service": FromOtherServiceException,
}


@api_view(["POST"])
def test_exceptions(request):
    """A view for testing exception handling."""
    raise exception_type_to_exception_mapping[request.query_params["exception_type"]]
