from collections import OrderedDict

from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response


class BaseEventsSerializer(serializers.Serializer):
    """Events serializer."""

    def get_fields(self):
        """Change fields repr to rabbit like routing keys."""
        fields = super().get_fields()
        out_fields = OrderedDict()
        for field_name, field in fields.items():
            out_fields[field_name.replace("__", ".")] = field
        return out_fields


def get_event_view(event_serializer: serializers.Serializer):
    """
    Return event view with dynamic set responses.

     Usage
        from toolset.django.event_view import get_event_view

        class EventsSerializer(serializers.Serializer):
            object__created = ObjectsCreatedEventSerializer()
            object__updated = ObjectsUpdatedEventSerializer()

        urlpatterns.append(url("api/v1/event-system-entities", get_event_view(EventsSerializer)))
    """
    event_serializer = type("", (event_serializer, BaseEventsSerializer), {})

    class EventEntitiesListView(viewsets.ViewSet):
        """Meta info for event entities based on serializers."""

        @swagger_auto_schema(  # noqa:  WPS125 Found builtin shadowing
            responses={status.HTTP_200_OK: event_serializer},
        )
        def list(self, request: Request, *args, **kwargs):
            """Shows current events schema."""
            return Response()

    return EventEntitiesListView.as_view({"get": "list"})
