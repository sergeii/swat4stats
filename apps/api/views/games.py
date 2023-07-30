from datetime import timedelta
from typing import Any

from django.db.models import Count, Prefetch, QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.api.filters import GameFilterSet
from apps.api.pagination import cursor_paginator_factory
from apps.api.serializers import (
    ServerBaseSerializer, MapSerializer,
    GameBaseSerializer, GameSerializer,
    GamePlayerHighlightSerializer
)
from apps.tracker.models import Server, Map, Game, Player, Objective, Procedure


class GameViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Game.objects.select_related('map', 'server').order_by('-pk')
    pagination_class = cursor_paginator_factory(page_size=50)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GameFilterSet

    def get_serializer_class(self) -> type[GameBaseSerializer]:
        match self.action:
            case 'retrieve':
                return GameSerializer
            case _:
                return GameBaseSerializer

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        match self.action:
            case 'retrieve' | 'highlights':
                return self._get_queryset_for_retrieve(queryset)
            case _:
                return queryset

    def _get_queryset_for_retrieve(self, queryset: QuerySet) -> QuerySet:
        player_qs = (
            Player.objects
            .select_related('loadout', 'alias', 'alias__isp', 'alias__profile', 'alias__profile__loadout')
            .prefetch_related('weapons')
            .exclude(dropped=True)
        )
        objective_qs = Objective.objects.order_by('pk')
        procedure_qs = Procedure.objects.order_by('-pk')

        prefetches = (
            Prefetch('objective_set', queryset=objective_qs),
            Prefetch('procedure_set', queryset=procedure_qs),
            Prefetch('player_set', queryset=player_qs),
        )

        return queryset.prefetch_related(*prefetches)

    @action(detail=True, methods=['get'], filter_backends=())
    def highlights(self, *args: Any, **kwargs: Any) -> Response:
        game = self.get_object()
        highlights = Game.objects.get_highlights_for_game(game)
        serializer_context = self.get_serializer_context()
        serializer = GamePlayerHighlightSerializer(highlights, context=serializer_context, many=True)
        return Response(serializer.data)


class PopularMapnamesViewSet(ListModelMixin, GenericViewSet):
    serializer_class = MapSerializer
    pagination_class = None

    max_maps = 100
    for_period = timedelta(days=180)

    def get_queryset(self) -> list[Map]:
        warehouse_map = Map.objects.using('replica').get(name='-EXP- Stetchkov Warehouse')
        # collect ids of top N most played maps
        # that have been seen since the specified number of days
        popular_maps_qs = (
            Game.objects
            .using('replica')
            .filter(date_finished__gte=timezone.now() - self.for_period)
            .order_by('map')
            .values('map')
            .annotate(game_cnt=Count('pk'))
            .order_by('-game_cnt')
        )[:self.max_maps]
        popular_maps_ids = [row['map'] for row in popular_maps_qs]

        popular_maps = Map.objects.filter(pk__in=popular_maps_ids)
        return sorted(
            popular_maps,
            key=lambda m: (m.pk > warehouse_map.pk, m.name.startswith('-EXP-'), m.name),
        )


class PopularServersViewSet(ListModelMixin, GenericViewSet):
    serializer_class = ServerBaseSerializer
    pagination_class = None

    max_servers = 50
    for_period = timedelta(days=180)

    def get_queryset(self) -> list[Server]:
        # get ids of the top N servers that have seen
        # the most games since the specified number of days
        popular_servers_qs = (
            Game.objects
            .using('replica')
            .filter(date_finished__gte=timezone.now() - self.for_period)
            .order_by('server')
            .values('server')
            .annotate(game_cnt=Count('pk'))
            .order_by('-game_cnt')
        )[:self.max_servers]
        # map server id to the number of played games,
        # so we can use the latter number to sort the servers
        # in the next query, where the ordering will be lost
        popular_servers_ids = {
            row['server']: row['game_cnt']
            for row in popular_servers_qs
        }

        popular_servers = Server.objects.filter(pk__in=popular_servers_ids)
        return sorted(
            popular_servers,
            key=lambda s: (-popular_servers_ids[s.pk], s.hostname or '', s.pk),
        )
