"""Snatched from https://github.com/encode/django-rest-framework/blob/master/tests/models.py ."""
from django.db import models


class RESTFrameworkModel(models.Model):
    """Base for test models that sets app_label, so they play nicely."""

    class Meta:
        app_label = "tests"
        abstract = True
