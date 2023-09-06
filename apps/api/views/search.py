from django.db.models import QuerySet
from rest_framework.generics import ListAPIView

from apps.api.filters import (
    SearchPlayersFilterBackend,
    SearchPlayersFilterSet,
    SearchServersFilterBackend,
    SearchServersFilterSet,
)
from apps.api.filters.base import ordering_filter_factory
from apps.api.pagination import limit_offset_pagination_factory
from apps.api.serializers import ProfileSearchItemSerializer, ServerSearchItemSerializer
from apps.tracker.models import Profile, Server


class SearchPlayersView(ListAPIView):
    serializer_class = ProfileSearchItemSerializer
    pagination_class = limit_offset_pagination_factory(default_limit=20, max_limit=100)
    filter_backends = (
        ordering_filter_factory(ordering_fields=["last_seen_at"]),
        SearchPlayersFilterBackend,
    )
    filterset_class = SearchPlayersFilterSet
    ordering = "-last_seen_at"

    def get_queryset(self) -> QuerySet[Profile]:
        return (
            Profile.objects.using("replica")
            .select_related("loadout")
            .filter(last_seen_at__isnull=False)
        )


class SearchServersView(ListAPIView):
    serializer_class = ServerSearchItemSerializer
    pagination_class = limit_offset_pagination_factory(default_limit=20, max_limit=100)
    filter_backends = (
        ordering_filter_factory(ordering_fields=["latest_game_played_at", "game_count"]),
        SearchServersFilterBackend,
    )
    filterset_class = SearchServersFilterSet
    ordering = "-latest_game_played_at"

    def get_queryset(self) -> QuerySet[Server]:
        return Server.objects.using("replica").filter(latest_game_played_at__isnull=False)
