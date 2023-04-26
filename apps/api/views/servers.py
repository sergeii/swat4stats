from django.http import Http404
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from apps.api.filters import ServerFilterBackend
from apps.api.pagination import paginator_factory
from apps.api.serializers import (
    ServerBaseSerializer, ServerCreateSerializer, ServerFullSerializer,
    PlayerStatSerializer,
)
from apps.tracker.managers import ServerQuerySet
from apps.tracker.models import Server, ServerStats
from apps.tracker.utils import get_current_stat_year


class ServerViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Server.objects.all()
    pagination_class = None
    filter_backends = (ServerFilterBackend,)
    lookup_value_regex = r'[^/]+'
    throttle_scope = 'servers'
    throttle_scope_methods = ['POST']

    def get_serializer_class(self) -> type[ServerBaseSerializer]:
        match self.action:
            case 'retrieve':
                return ServerFullSerializer
            case 'create':
                return ServerCreateSerializer
            case _:
                return ServerBaseSerializer

    def get_queryset(self) -> ServerQuerySet:
        queryset = super().get_queryset()
        match self.action:
            case 'retrieve':
                return queryset.select_related('merged_into').order_by()
            case 'list':
                return queryset.listed().order_by('pk').with_status()
            case _:
                return queryset

    def get_object(self) -> Server:
        pk_or_addr = self.kwargs[self.lookup_field]

        # obtain server by its ip:port
        if ':' in pk_or_addr:
            ip, port = pk_or_addr.split(':', 1)
            filters = {
                'ip': ip,
                'port': port,
            }
        elif not pk_or_addr.isdigit():
            raise Http404()
        else:
            filters = {
                'pk': pk_or_addr
            }

        queryset = self.get_queryset().filter(**filters)[:1]
        servers: list[Server] = queryset.with_status(with_empty=True)

        try:
            server = servers[0]
        except IndexError:
            raise Http404()

        if not (server.enabled or server.merged_into_id is not None):
            raise Http404()

        return server


class ServerLeaderboardViewSet(ListModelMixin, GenericViewSet):
    queryset = ServerStats.objects.all()
    serializer_class = PlayerStatSerializer
    pagination_class = paginator_factory(page_size=20, ordering=('position', 'id'))

    def get_queryset(self):
        return (ServerStats.objects
                .select_related('profile', 'profile__loadout')
                .filter(year=get_current_stat_year()))
