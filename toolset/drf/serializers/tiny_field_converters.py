import typing as tp

from rest_framework import serializers

from toolset.drf.serializers import PrimaryKeyRelatedNestedField


def make_tiny_any_field(
    parent: serializers.Serializer, field_name: str, field: serializers.Field, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Return as is."""
    return {field_name: field.__class__(**kwargs)}


def make_tiny_null_boolean(
    parent: serializers.Serializer, field_name: str, field: serializers.ChoiceField, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Return as is almost."""
    kwargs.pop("allow_null")
    return {field_name: serializers.NullBooleanField(**kwargs)}


def make_tiny_choice(
    parent: serializers.Serializer, field_name: str, field: serializers.ChoiceField, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Choice to char field."""
    return {field_name: serializers.CharField(**kwargs)}


def make_tiny_list(
    parent: serializers.Serializer, field_name: str, field: serializers.ListField, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """List(Choice) to List(char) or as is."""
    if isinstance(field.child, serializers.ChoiceField):
        return {field_name: serializers.ListField(child=serializers.CharField(), **kwargs)}
    return make_tiny_any_field(parent, field_name, field, **kwargs)


def make_tiny_primary_key_related(
    parent: serializers.Serializer,
    field_name: str,
    field: serializers.PrimaryKeyRelatedField,
    **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Primary key to int field."""
    # Danger!!! PK can be str.
    clear_source_field, *_ = field.source.split("_id")
    kwargs["source"] = f"{clear_source_field}_id"
    if field_name == kwargs["source"]:
        kwargs.pop("source")
    return {field_name: serializers.IntegerField(**kwargs)}


def make_tiny_pk_related_nested(
    parent: serializers.Serializer, field_name: str, field: PrimaryKeyRelatedNestedField, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Return as is."""
    return make_tiny_any_field(
        parent,
        field_name,
        field,
        serializer_class=field.serializer_class,
        queryset=field.queryset,
        **kwargs,
    )


def make_tiny_m2m_related(
    parent: serializers.Serializer, field_name: str, field: serializers.ManyRelatedField, **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Return as is."""
    # Django does not let you set the same source and field_name, but somehow in
    # value.child_relation (which is a serializer passed to ManyRelatedField) both
    # these fields are empty strings
    if field.child_relation.source == "":
        field.child_relation.source = None
    return {field_name: serializers.ManyRelatedField(child_relation=field.child_relation, **kwargs)}


def make_tiny_serializer_method(
    parent: serializers.Serializer,
    field_name: str,
    field: serializers.SerializerMethodField,
    **kwargs,
) -> tp.Dict[str, serializers.Field]:
    """Copy method."""
    method = getattr(parent.__class__, field.method_name)
    return {field_name: field, field.method_name: method}
