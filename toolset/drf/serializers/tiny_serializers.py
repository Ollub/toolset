import types
import typing as tp

from rest_framework import serializers
from rest_framework.fields import empty

from toolset.drf.serializers import PrimaryKeyRelatedNestedField
from toolset.drf.serializers import tiny_field_converters as converters


def _make_tiny_inner_serializer(
    parent: tp.Union[serializers.Serializer, serializers.ListSerializer],
    field_name: str,
    field: tp.Union[serializers.Serializer, serializers.ListSerializer],
    **kwargs,
) -> tp.Dict[str, serializers.Serializer]:
    """Make tiny inner serializers."""
    sub_parent = field
    if isinstance(field, serializers.Serializer):
        created_serializer = _TinyOptions.created_serializers.get(f"Tiny{field.__class__.__name__}")
    elif isinstance(field, serializers.ListSerializer):
        created_serializer = _TinyOptions.created_serializers.get(
            f"Tiny{field.child.__class__.__name__}",
        )
        kwargs["many"] = True
        sub_parent = field.child
    else:
        return {}

    if created_serializer:
        return {field_name: created_serializer(**kwargs)}
    return {field_name: make_tiny(sub_parent)(**kwargs)}


class _TinyOptions:
    """Contains convertation options/methods/field_names etc."""

    created_serializers: tp.Dict[str, tp.Type[serializers.Serializer]] = {}
    converters = types.MappingProxyType(
        {
            serializers.ChoiceField: converters.make_tiny_choice,
            serializers.NullBooleanField: converters.make_tiny_null_boolean,
            serializers.ListField: converters.make_tiny_list,
            serializers.PrimaryKeyRelatedField: converters.make_tiny_primary_key_related,
            PrimaryKeyRelatedNestedField: converters.make_tiny_pk_related_nested,
            serializers.ManyRelatedField: converters.make_tiny_m2m_related,
            serializers.SerializerMethodField: converters.make_tiny_serializer_method,
            serializers.Serializer: _make_tiny_inner_serializer,
            serializers.ListSerializer: _make_tiny_inner_serializer,
        },
    )
    important_methods = ("to_representation",)
    common_attrs = ("required", "allow_blank", "allow_null", "default")
    required_field_attrs = types.MappingProxyType(
        {serializers.DecimalField: {"max_digits", "decimal_places"}},
    )


def make_tiny_field(
    parent: serializers.Serializer,
    field_name: str,
    field: serializers.SerializerMethodField,
    **field_attrs,
) -> tp.Dict[str, serializers.Field]:
    """Make serializer field tiny."""
    # check if we have separate function to convert
    field_type = type(field)
    tiny_maker = _TinyOptions.converters.get(field_type, None)
    if tiny_maker is not None:
        return tiny_maker(parent, field_name, field, **field_attrs)

    return converters.make_tiny_any_field(parent, field_name, field, **field_attrs)


def extract_field_attributes(field_name: str, field: serializers.Field):
    """Extract important field attrs."""
    attrs = {}
    required_field_attrs = _TinyOptions.required_field_attrs.get(type(field), set())
    for attr_name in set(_TinyOptions.common_attrs).union(required_field_attrs):
        attr_value = getattr(field, attr_name, empty)
        if attr_value is not empty:
            attrs[attr_name] = attr_value

    source = field.source
    if source != field_name:
        # if source and key are the same it means field by default
        # e.g. user_id = serializers.IntegerField()  noqa: E800 commented out code
        # but we can't specify its args because field and source with same name produce
        # DRF error smth like "Do not specify source if field has same name"
        attrs["source"] = source
    return attrs


def make_tiny(serializer: serializers.Serializer) -> tp.Type[serializers.Serializer]:
    """Make serializer tiny."""
    tiny_s = _TinyOptions.created_serializers.get(f"Tiny{serializer.__class__.__name__}")
    if tiny_s:
        return tiny_s

    old_fields = serializer.fields
    new_fields = {}
    for field_name, field in old_fields.items():
        attrs = extract_field_attributes(field_name, field)
        if isinstance(field, (serializers.Serializer, serializers.ListSerializer)):
            new_fields.update(_make_tiny_inner_serializer(serializer, field_name, field, **attrs))
        else:
            new_fields.update(make_tiny_field(serializer, field_name, field, **attrs))

    for method_name in _TinyOptions.important_methods:
        method = getattr(serializer.__class__, method_name)
        new_fields[method_name] = method

    tiny_s = type(f"Tiny{serializer.__class__.__name__}", (serializers.Serializer,), new_fields)
    _TinyOptions.created_serializers[f"Tiny{serializer.__class__.__name__}"] = tiny_s
    return tiny_s
