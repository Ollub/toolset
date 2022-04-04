from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.db import models
from rest_framework import serializers

from toolset.drf.serializers import PrimaryKeyRelatedNestedField, make_tiny


class SomeChoices(models.TextChoices):
    """SomeChoices."""

    first = "first", "first"
    second = "second", "second"


class AnotherModel(models.Model):
    """Another model."""

    text = models.TextField()

    class Meta:
        app_label = "tests"


class OneMoreModel(models.Model):
    """OneMore model."""

    class Meta:
        app_label = "tests"


class SomeModel(models.Model):
    """SomeModel."""

    text = models.TextField()
    choice = models.TextField(choices=SomeChoices.choices)
    decimal = models.DecimalField(max_digits=6, decimal_places=5)
    list_of_text = ArrayField(models.TextField())
    list_of_choices = ArrayField(models.TextField(choices=SomeChoices.choices))
    another = models.ForeignKey(AnotherModel, on_delete=models.CASCADE)
    another_m2m = models.ManyToManyField(AnotherModel)
    one_more = models.ForeignKey(OneMoreModel, on_delete=models.CASCADE)

    class Meta:
        app_label = "tests"


class InnerSerializer(serializers.Serializer):
    """InnerSerializer."""

    field = serializers.CharField()
    req_field = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    non_req_field = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    null_field = serializers.NullBooleanField(default=None)


class SecondInnerSerializer(serializers.Serializer):
    """SecondInnerSerializer."""

    field = serializers.CharField()


class AnotherSerializer(serializers.ModelSerializer):
    """Another serializer."""

    class Meta:
        model = AnotherModel
        fields = "__all__"


class SomeSerializer(serializers.ModelSerializer):
    """SomeSerializer."""

    other_source = serializers.CharField(source="text", allow_blank=True, allow_null=True)
    other_method = serializers.SerializerMethodField()
    default_field = serializers.CharField(default="default")
    inner = InnerSerializer()
    another_inner = InnerSerializer()
    inner_many = InnerSerializer(many=True)
    second_inner_many = SecondInnerSerializer(many=True)
    another = PrimaryKeyRelatedNestedField(AnotherSerializer, queryset=AnotherModel.objects.all())
    another_id = PrimaryKeyRelatedNestedField(
        AnotherSerializer, queryset=AnotherModel.objects.all(), source="another",
    )
    one_more_id = serializers.PrimaryKeyRelatedField(queryset=OneMoreModel.objects.all())
    another_simple = serializers.PrimaryKeyRelatedField(
        queryset=AnotherModel.objects.all(), source="another",
    )

    class Meta:
        model = SomeModel
        exclude = ["id"]

    def get_other_method(self, instance):
        """Get other method."""
        return instance.text


def test_tiny_serializer():
    """Test tiny serializer gives same data as usual one."""
    model = SomeModel(
        text="text",
        choice=SomeChoices.first,
        list_of_text=["one", "two"],
        list_of_choices=[SomeChoices.first, SomeChoices.second],
        decimal=Decimal("3.1415926535"),
    )
    inner_data = {
        "field": "data",
        "req_field": "req_data",
    }
    model.inner = inner_data
    model.another_inner = inner_data
    model.inner_many = [inner_data, inner_data]
    model.second_inner_many = [inner_data, inner_data]

    tiny_serializer = make_tiny(SomeSerializer())
    assert dict(tiny_serializer(model).data) == {
        **SomeSerializer(model).data,
        "default_field": "default",
    }


def test_tiny_serializer_created_once():
    """Test in case of re-creation cached serializer class returned."""
    tiny_serializer1 = make_tiny(SomeSerializer())
    tiny_serializer2 = make_tiny(SomeSerializer())

    assert id(tiny_serializer1) == id(tiny_serializer2)
