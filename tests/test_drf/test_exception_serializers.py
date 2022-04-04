from toolset.drf.exceptions_utils.serializers import ListErrorRepresentationSerializer
from tests.django.exceptions import CustomException, ExceptionWithMapping


def test_list_error_representation_serializer():
    """Tests that ListErrorRepresentationSerializer can represent several errors for Swagger.

    Tests that ListErrorRepresentationSerializer have all given custom exceptions with the right
    structure.
    """
    serializer = ListErrorRepresentationSerializer([CustomException, ExceptionWithMapping])
    assert "CustomException" in serializer.fields
    assert "ExceptionWithMapping" in serializer.fields

    for error_serializer in serializer.fields.values():
        assert error_serializer.data == {
            "error_schema": {"detail": {"field_name": []}, "error_code": ""},
            "default_detail": "",
        }
