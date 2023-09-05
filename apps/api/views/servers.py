from typing import ClassVar

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from apps.api.filters import ServerFilterBackend
from apps.api.pagination import cursor_paginator_factory
from apps.api.serializers import (
    PlayerStatSerializer,
    ServerBaseSerializer,
    ServerCreateSerializer,
    ServerFullSerializer,
)
from apps.tracker.managers import ServerQuerySet
from apps.tracker.models import Server, ServerStats
from apps.tracker.utils.misc import get_current_stat_year


class ServerViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Server.objects.all()
    pagination_class = None
    filter_backends = (ServerFilterBackend,)
    lookup_value_regex = r"[^/]+"
    throttle_scope = "servers"
    throttle_scope_methods: ClassVar[list[str]] = ["POST"]

    def get_serializer_class(self) -> type[ServerBaseSerializer]:
        match self.action:
            case "retrieve":
                return ServerFullSerializer
            case "create":
                return ServerCreateSerializer
            case _:
                return ServerBaseSerializer

    def get_queryset(self) -> ServerQuerySet:
        queryset = super().get_queryset()
        match self.action:
            case "retrieve":
                return queryset.select_related("merged_into").order_by()
            case "list":
                return queryset.listed().order_by("pk").with_status()
            case _:
                return queryset

    def get_object(self) -> Server:
        pk_or_addr = self.kwargs[self.lookup_field]

        # obtain server by its ip:port
        if ":" in pk_or_addr:
            ip, port = pk_or_addr.split(":", 1)
            filters = {
                "ip": ip,
                "port": port,
            }
        elif not pk_or_addr.isdigit():
            raise Http404
        else:
            filters = {"pk": pk_or_addr}

        queryset = self.get_queryset().filter(**filters)[:1]
        servers: list[Server] = queryset.with_status(with_empty=True)

        try:
            server = servers[0]
        except IndexError:
            raise Http404

        if not (server.enabled or server.merged_into_id is not None):
            raise Http404

        return server


class ServerLeaderboardViewSet(ListModelMixin, GenericViewSet):
    queryset = ServerStats.objects.all()
    serializer_class = PlayerStatSerializer
    pagination_class = cursor_paginator_factory(page_size=20, ordering=("position", "id"))

    def get_queryset(self) -> ServerQuerySet:
        return ServerStats.objects.select_related("profile", "profile__loadout").filter(
            year=get_current_stat_year()
        )


class PopularServersViewSet(ListModelMixin, GenericViewSet):
    serializer_class = ServerBaseSerializer
    pagination_class = None

    max_servers = 50

    def get_queryset(self) -> QuerySet[Server]:
        qs = Server.objects.filter(rating__isnull=False).order_by("rating", "-game_count")
        return qs[: self.max_servers]
