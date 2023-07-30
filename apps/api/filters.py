from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import QuerySet, F
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.api.serializers import ServerFilterSerializer
from apps.tracker.models import Game, Server, Profile


class ServerFilterBackend(DjangoFilterBackend):
    serializer_class = ServerFilterSerializer

    def filter_queryset(self, request: Request, objects: QuerySet[Server], view: GenericViewSet) -> list[Server]:
        objects = super().filter_queryset(request, objects, view)

        filter_serializer = self.serializer_class(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        for param, value in filter_serializer.validated_data.items():
            # default value
            if value is None:
                continue

            filter_method = getattr(self, f'filter_{param}')
            filtered_objects = (filter_method(obj, value) for obj in objects)
            objects = [obj for obj in filtered_objects if obj]

        return objects

    def filter_full(self, object: Server, value: bool) -> Server | None:
        if (object.status['numplayers'] == object.status['maxplayers']) == value:
            return object
        return None

    def filter_empty(self, object: Server, value: bool) -> Server | None:
        if (object.status['numplayers'] == 0) == value:
            return object
        return None

    def filter_passworded(self, object: Server, value: bool) -> Server | None:
        if object.status['password'] == value:
            return object
        return None

    def filter_gamename(self, object: Server, value: str) -> Server | None:
        if object.status['gamevariant'] == value:
            return object
        return None

    def filter_gamever(self, object: Server, value: str) -> Server | None:
        if object.status['gamever'] == value:
            return object
        return None

    def filter_gametype(self, object: Server, value: str) -> Server | None:
        if object.status['gametype'] == value:
            return object
        return None

    def filter_mapname(self, object: Server, value: str) -> Server | None:
        if object.status['mapname'] == value:
            return object
        return None


class GameFilterSet(django_filters.FilterSet):
    day = django_filters.NumberFilter(field_name='date_finished', lookup_expr='day')
    month = django_filters.NumberFilter(field_name='date_finished', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='date_finished', lookup_expr='year')

    class Meta:
        model = Game
        fields = ['server', 'map', 'gametype', 'day', 'month', 'year']


class SearchFilterBackend(django_filters.rest_framework.DjangoFilterBackend):

    def filter_queryset(self, request: Request, queryset: QuerySet[Profile], view: GenericViewSet) -> QuerySet[Profile]:
        queryset = super().filter_queryset(request, queryset, view)
        ordering = ('-last_seen_at', 'pk')

        if query := request.query_params.get('q'):
            sq = SearchQuery(query, search_type='phrase', config='simple')
            return (
                queryset
                .filter(search=sq)
                .annotate(rank=SearchRank(F('search'), sq))
                .order_by('-rank', *ordering)
            )

        return queryset.order_by(*ordering)


class SearchFilterSet(django_filters.FilterSet):
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')
