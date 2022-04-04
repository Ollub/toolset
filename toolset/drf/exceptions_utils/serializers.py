from rest_framework import serializers
from rest_framework.settings import api_settings

from toolset.typing_helpers import JSON


class _DefaultDetailSchema(serializers.Serializer):
    """Schema for error detail."""

    field_name = serializers.ListField()


class _ErrorSchemaSerializer(serializers.Serializer):
    """Serializer to represent single error in swagger."""

    def __init__(self, error, **kwargs) -> None:
        """Init."""
        super().__init__(**kwargs)
        self._error = error
        self.ref_name = error.__name__

    def get_fields(self) -> JSON:
        """Get representation of error for swagger."""
        return {
            "detail": getattr(self._error, "detail_schema", _DefaultDetailSchema)(),
            "error_code": serializers.CharField(default=self._error.default_code),
        }

    class Meta:
        ref_name = None


class ErrorRepresentationSerializer(serializers.Serializer):
    """Serializer to represent single error in swagger."""

    def __init__(self, error, **kwargs) -> None:
        """Init."""
        super().__init__(**kwargs)
        self._error = error
        self.ref_name = error.__name__

    def get_fields(self) -> JSON:
        """Get representation of error for swagger."""
        return {
            "error_schema": _ErrorSchemaSerializer(self._error),
            "default_detail": serializers.CharField(
                default={api_settings.NON_FIELD_ERRORS_KEY: [self._error.default_detail]},
            ),
        }

    class Meta:
        ref_name = None


class ListErrorRepresentationSerializer(serializers.Serializer):
    """Serializer to represent list of errors in Swagger."""

    def __init__(self, list_errors) -> None:
        """Init."""
        super().__init__()
        self._list_errors = list_errors

    def get_fields(self) -> JSON:
        """Get representation of errors for Swagger."""
        fields = {}
        for error in self._list_errors:
            fields[error.__name__] = ErrorRepresentationSerializer(error=error)
        return fields

    class Meta:
        ref_name = None
