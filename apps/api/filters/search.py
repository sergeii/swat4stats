import django_filters
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db import models
from django.db.models import QuerySet, F, Value, OuterRef, Subquery
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.tracker.models import Profile, Alias, Server


class SearchPlayersFilterBackend(django_filters.rest_framework.DjangoFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet[Profile], view: GenericViewSet
    ) -> QuerySet[Profile]:
        queryset = super().filter_queryset(request, queryset, view)
        ordering = (*queryset.query.order_by, "pk")

        if search_term := request.query_params.get("q"):
            return self._filter_queryset_with_term(queryset, search_term, ordering)

        # fmt: off
        return (
            queryset
            .annotate(
                headline=F("name"),
                excerpt=Value("", output_field=models.TextField()),
            )
            .order_by(*ordering)
        )
        # fmt: on

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
                headline=SearchHeadline(F("name"), sq_headline, highlight_all=True),
                rank=SearchRank(F("search"), sq),
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


class SearchPlayersFilterSet(django_filters.FilterSet):
    country = django_filters.CharFilter(field_name="country", lookup_expr="iexact")


class SearchServersFilterBackend(django_filters.rest_framework.DjangoFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet[Server], view: GenericViewSet
    ) -> QuerySet[Server]:
        queryset = super().filter_queryset(request, queryset, view)
        ordering = (*queryset.query.order_by, "pk")

        if search_term := request.query_params.get("q"):
            return self._filter_queryset_with_term(queryset, search_term, ordering)

        return queryset.annotate(headline=F("hostname_clean")).order_by(*ordering)

    def _filter_queryset_with_term(
        self,
        queryset: QuerySet[Server],
        term: str,
        ordering: tuple[str, ...],
    ) -> QuerySet[Server]:
        sq = SearchQuery(term, search_type="plain", config="simple")
        sq_headline = SearchQuery(term, search_type="plain", config="english")

        return (
            queryset.filter(search=sq)
            .annotate(
                headline=SearchHeadline(F("hostname_clean"), sq_headline),
                rank=SearchRank(F("search"), sq),
            )
            .order_by("-rank", *ordering)
        )


class SearchServersFilterSet(django_filters.FilterSet):
    country = django_filters.CharFilter(field_name="country", lookup_expr="iexact")
