import typing as tp

from rest_framework import serializers

if tp.TYPE_CHECKING:
    from django.db.models import Model


class PrimaryKeyRelatedNestedField(serializers.PrimaryKeyRelatedField):
    """Nested PK field for serialization via serializer."""

    def __init__(self, serializer_class: tp.Type[serializers.Serializer], **kwargs):
        """Init with serializer class."""
        self.serializer_class = serializer_class
        super().__init__(**kwargs)

    def to_representation(self, value: "Model") -> serializers.Serializer.data:
        """Override default representation for serializer data."""
        return self.serializer_class(value).data

    def use_pk_only_optimization(self):
        """Use full values, not only pk."""
        return False
