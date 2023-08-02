from typing import ClassVar

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db import models
from django.db.models import QuerySet, F, Value, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.api.serializers import ServerFilterSerializer
from apps.tracker.models import Game, Server, Profile, Alias


class ServerFilterBackend(DjangoFilterBackend):
    serializer_class = ServerFilterSerializer

    def filter_queryset(
        self, request: Request, objects: QuerySet[Server], view: GenericViewSet
    ) -> list[Server]:
        objects = super().filter_queryset(request, objects, view)

        filter_serializer = self.serializer_class(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        for param, value in filter_serializer.validated_data.items():
            # default value
            if value is None:
                continue

            filter_method = getattr(self, f"filter_{param}")
            filtered_objects = (filter_method(obj, value) for obj in objects)
            objects = [obj for obj in filtered_objects if obj]

        return objects

    def filter_full(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if (obj.status["numplayers"] == obj.status["maxplayers"]) == value:
            return obj
        return None

    def filter_empty(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if (obj.status["numplayers"] == 0) == value:
            return obj
        return None

    def filter_passworded(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if obj.status["password"] == value:
            return obj
        return None

    def filter_gamename(self, obj: Server, value: str) -> Server | None:
        if obj.status["gamevariant"] == value:
            return obj
        return None

    def filter_gamever(self, obj: Server, value: str) -> Server | None:
        if obj.status["gamever"] == value:
            return obj
        return None

    def filter_gametype(self, obj: Server, value: str) -> Server | None:
        if obj.status["gametype"] == value:
            return obj
        return None

    def filter_mapname(self, obj: Server, value: str) -> Server | None:
        if obj.status["mapname"] == value:
            return obj
        return None


class GameFilterSet(django_filters.FilterSet):
    day = django_filters.NumberFilter(field_name="date_finished", lookup_expr="day")
    month = django_filters.NumberFilter(field_name="date_finished", lookup_expr="month")
    year = django_filters.NumberFilter(field_name="date_finished", lookup_expr="year")

    class Meta:
        model = Game
        fields: ClassVar[list[str]] = ["server", "map", "gametype", "day", "month", "year"]


class SearchFilterBackend(django_filters.rest_framework.DjangoFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet[Profile], view: GenericViewSet
    ) -> QuerySet[Profile]:
        queryset = super().filter_queryset(request, queryset, view)
        ordering = ("-last_seen_at", "pk")

        if search_term := request.query_params.get("q"):
            return self._filter_queryset_with_term(queryset, search_term, ordering)

        return queryset.annotate(
            headline=F("name"),
            excerpt=Value("", output_field=models.TextField()),
        ).order_by(*ordering)

    def _filter_queryset_with_term(
        self,
        queryset: QuerySet[Profile],
        term: str,
        ordering: tuple[str, ...],
    ) -> QuerySet[Profile]:
        sq = SearchQuery(term, search_type="phrase", config="simple")
        sq_headline = SearchQuery(term, search_type="plain", config="english")

        matching_alias_excerpt_sub = (
            Alias.objects.filter(
                profile_id=OuterRef("pk"),
                search=sq,
            )
            .exclude(name=OuterRef("name"))
            .annotate(
                headline=SearchHeadline(F("name"), sq_headline), rank=SearchRank(F("search"), sq)
            )
            .order_by("-rank")
            .values("headline")
        )[:1]

        return (
            queryset.filter(search=sq)
            .annotate(
                headline=SearchHeadline(F("name"), sq_headline),
                excerpt=Subquery(matching_alias_excerpt_sub),
                rank=SearchRank(F("search"), sq),
            )
            .order_by("-rank", *ordering)
        )


class SearchFilterSet(django_filters.FilterSet):
    country = django_filters.CharFilter(field_name="country", lookup_expr="iexact")
