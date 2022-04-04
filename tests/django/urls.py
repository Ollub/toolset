from django.urls import path

from tests.django.views import test_exceptions

urlpatterns = [
    path("test_exceptions", test_exceptions, name="test_exceptions"),
]
