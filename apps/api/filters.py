from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from apps.api.serializers import ServerFilterSerializer
from apps.tracker.models import Game


class ServerFilterBackend(DjangoFilterBackend):
    serializer_class = ServerFilterSerializer

    def filter_queryset(self, request, objects, view):
        objects = super().filter_queryset(request, objects, view)

        filter_serializer = self.serializer_class(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        for param, value in filter_serializer.validated_data.items():
            # default value
            if value is None:
                continue

            filter_method = getattr(self, 'filter_%s' % param)
            filtered_objects = (filter_method(obj, value) for obj in objects)
            objects = [obj for obj in filtered_objects if obj]

        return objects

    def filter_full(self, object, value):
        if (object.status['numplayers'] == object.status['maxplayers']) == value:
            return object

    def filter_empty(self, object, value):
        if (object.status['numplayers'] == 0) == value:
            return object

    def filter_passworded(self, object, value):
        if object.status['password'] == value:
            return object

    def filter_gamename(self, object, value):
        if object.status['gamevariant'] == value:
            return object

    def filter_gamever(self, object, value):
        if object.status['gamever'] == value:
            return object

    def filter_gametype(self, object, value):
        if object.status['gametype'] == value:
            return object

    def filter_mapname(self, object, value):
        if object.status['mapname'] == value:
            return object


class GameFilter(django_filters.FilterSet):
    day = django_filters.NumberFilter(field_name='date_finished', lookup_expr='day')
    month = django_filters.NumberFilter(field_name='date_finished', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='date_finished', lookup_expr='year')

    class Meta:
        model = Game
        fields = ['server', 'map', 'gametype', 'day', 'month', 'year']
