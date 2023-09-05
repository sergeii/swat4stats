from typing import Any

from django.db.models import Prefetch, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.api.filters import GameFilterSet
from apps.api.pagination import cursor_paginator_factory
from apps.api.serializers import GameBaseSerializer, GamePlayerHighlightSerializer, GameSerializer
from apps.tracker.models import Game, Objective, Player, Procedure


class GameViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Game.objects.select_related("map", "server").order_by("-pk")
    pagination_class = cursor_paginator_factory(page_size=50)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GameFilterSet

    def get_serializer_class(self) -> type[GameBaseSerializer]:
        match self.action:
            case "retrieve":
                return GameSerializer
            case _:
                return GameBaseSerializer

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        match self.action:
            case "retrieve" | "highlights":
                return self._get_queryset_for_retrieve(queryset)
            case _:
                return queryset

    def _get_queryset_for_retrieve(self, queryset: QuerySet) -> QuerySet:
        player_qs = (
            Player.objects.select_related(
                "loadout", "alias", "alias__isp", "alias__profile", "alias__profile__loadout"
            )
            .prefetch_related("weapons")
            .exclude(dropped=True)
        )
        objective_qs = Objective.objects.order_by("pk")
        procedure_qs = Procedure.objects.order_by("-pk")

        prefetches = (
            Prefetch("objective_set", queryset=objective_qs),
            Prefetch("procedure_set", queryset=procedure_qs),
            Prefetch("player_set", queryset=player_qs),
        )

        return queryset.prefetch_related(*prefetches)

    @action(detail=True, methods=["get"], filter_backends=())
    def highlights(self, *args: Any, **kwargs: Any) -> Response:
        game = self.get_object()
        highlights = Game.objects.get_highlights_for_game(game)
        serializer_context = self.get_serializer_context()
        serializer = GamePlayerHighlightSerializer(
            highlights, context=serializer_context, many=True
        )
        return Response(serializer.data)
