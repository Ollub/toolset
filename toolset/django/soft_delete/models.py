import typing as tp

from django.db import models
from django.db.models import Manager, QuerySet
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# __set__ value type
_ST = tp.TypeVar("_ST")
# __get__ return type
_GT = tp.TypeVar("_GT")


class UpdatedAtQueryset(QuerySet):
    """Usual queryset with overridden update method."""

    def update(self, **kwargs) -> int:
        """We should set updated_at field during update."""
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = timezone.now()
        return super().update(**kwargs)


_base_updated_manager_class = Manager.from_queryset(UpdatedAtQueryset)


class UpdatedAtManager(_base_updated_manager_class):  # type: ignore
    """Change base manager to use with UpdatedAtQueryset."""


def _copy_fields(field: "models.Field[_ST, _GT]") -> "models.Field[_ST, _GT]":
    if isinstance(field, models.ForeignKey):
        # in deleted schema there is no relations
        return models.BigIntegerField(null=field.null)

    # basically, do a field.clone() operation, but remove constraints
    *_, args, kwargs = field.deconstruct()
    for unique in ("unique", "unique_for_date", "unique_for_month", "unique_for_year"):
        kwargs.pop(unique, None)
    return field.__class__(*args, **kwargs)


class DeletedMeta(ModelBase):
    """Metaclass which created twin deleted class for original class."""

    def __new__(mcs, name, bases, attrs):  # noqa: N804 cls -> mcs
        """New."""
        klass = tp.cast("SoftDeletableABC", super().__new__(mcs, name, bases, attrs))
        klass_meta = klass._meta  # noqa: WPS437 protected
        if klass_meta.abstract or name.startswith("Deleted"):
            return klass

        fields = {field.attname: _copy_fields(field) for field in klass_meta.fields}

        class Meta:  # noqa: WPS431 nested meta
            db_table = f"deleted_{klass_meta.db_table}"

        deleted_name = f"Deleted{name}"
        deleted_class = tp.cast(
            "SoftDeletableABC",
            type(
                deleted_name,
                (models.Model,),
                {**fields, "__module__": bases[0].__module__, "Meta": Meta},
            ),
        )

        globals()[deleted_name] = deleted_class  # noqa: WPS421 globals usage

        klass._deleted_model = deleted_class  # noqa: WPS437  protected attr
        return klass


class SoftDeletableABC(models.Model, metaclass=DeletedMeta):
    """
    Abstract class for soft deleted models.

    There is the "deleted" schema which is almost a full copy of public.
    There are several db functions that we use in soft delete. (sql.py::soft_delete_functions_sql)
    1) `soft_delete` - before actual deletion it will copy data row into "deleted" schema and set `deleted_at`
    2) `soft_restore` - move from "deleted" schema to public on unset `deleted_at`

    On each `SoftDeletionModel` we create a copy table in "deleted" schema (with some restrictions, see _copy_fields).

    On each `SoftDeletionModel` subclass table we create trigger `BEFORE DELETE` with `soft_delete` function
    (sql.py::get_soft_delete_sql_triggers)

    After that each migration on original model will also create migration for Deleted model.
    """

    deleted_at = models.DateTimeField(_("Delete date"), blank=True, null=True)
    updated_at = models.DateTimeField(_("Update date"), blank=True, null=True, auto_now=True)
    created_at = models.DateTimeField(_("Create date"), blank=True, null=True, auto_now_add=True)

    objects = UpdatedAtManager()

    _deleted_model: models.Model

    class Meta:
        abstract = True

    @classmethod
    def restore(cls, query: models.Q):
        """Restore rows from provided query."""
        return cls._deleted_model.objects.filter(query).update(deleted_at=None)
