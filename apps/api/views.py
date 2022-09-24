from django.db.models import Count, Case, When, Value, BooleanField, Prefetch
from django.http import Http404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from django_filters.rest_framework import DjangoFilterBackend

from apps.api.pagination import paginator_factory
from apps.news.models import Article
from apps.tracker.models import Server, Map, Game, Player, Objective, Procedure, ServerStats
from apps.api.serializers import (ServerBaseSerializer, ServerFullSerializer,
                                  NewsArticleSerializer, MapSerializer,
                                  GameBaseSerializer, GameSerializer,
                                  GamePlayerHighlightSerializer,
                                  PlayerStatSerializer)
from apps.api.filters import ServerFilterBackend, GameFilter
from apps.tracker.utils import get_current_stat_year


class ArticleViewSet(ListModelMixin, GenericViewSet):
    queryset = Article.objects.all()
    serializer_class = NewsArticleSerializer
    pagination_class = None

    def get_queryset(self):
        return super().get_queryset().latest_published(5)


class ServerViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Server.objects.listed().order_by('-pinned', 'pk')
    pagination_class = None
    filter_backends = (ServerFilterBackend,)
    lookup_value_regex = r'[^/]+'
    throttle_scope = 'servers'
    throttle_scope_methods = ['POST']

    def get_serializer_class(self):
        if self.action in ('list',):
            return ServerBaseSerializer
        return ServerFullSerializer

    def get_queryset(self):
        return super().get_queryset().with_status()

    def get_object(self):
        pk_or_addr = self.kwargs[self.lookup_field]

        # obtain server by its ip:port
        if ':' in pk_or_addr:
            ip, port = pk_or_addr.split(':', 1)
            filters = {
                'ip': ip,
                'port': port,
            }
        else:
            filters = {
                'pk': pk_or_addr
            }

        queryset = super().get_queryset().filter(**filters).with_status()

        if not queryset:
            raise Http404()

        return queryset[0]


class GameViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Game.objects.select_related('map', 'server').order_by('-pk')
    pagination_class = paginator_factory(page_size=50)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GameFilter

    def get_serializer_class(self):
        if self.action in ('retrieve',):
            return GameSerializer
        return GameBaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        prefetch_list = ()

        if self.action in ('retrieve', 'highlights'):
            player_qs = (Player.objects
                         .select_related('loadout', 'alias', 'alias__isp', 'alias__profile')
                         .prefetch_related('weapons')
                         .exclude(dropped=True))
            objective_qs = Objective.objects.order_by('pk')
            procedure_qs = Procedure.objects.order_by('-pk')
            prefetch_list += (
                Prefetch('objective_set', queryset=objective_qs),
                Prefetch('procedure_set', queryset=procedure_qs),
                Prefetch('player_set', queryset=player_qs),
            )

        if prefetch_list:
            queryset = queryset.prefetch_related(*prefetch_list)

        return queryset

    @action(detail=True, methods=['get'], filter_backends=())
    def highlights(self, *args, **kwargs):
        game = self.get_object()
        highlights = game._get_player_highlights()
        serializer_context = self.get_serializer_context()
        data = GamePlayerHighlightSerializer(highlights, context=serializer_context, many=True).data
        return Response(data)


class PopularMapnamesViewSet(ListModelMixin, GenericViewSet):
    serializer_class = MapSerializer
    pagination_class = None

    def get_queryset(self):
        warehouse_map = Map.objects.get(name='-EXP- Stetchkov Warehouse')
        queryset = (Map.objects
                    .annotate(game_num=Count('game'),
                              is_builtin_map=Case(When(pk__lte=warehouse_map.pk,
                                                       then=Value(True)),
                                                  default=Value(False),
                                                  output_field=BooleanField()))
                    .filter(game_num__gt=0)
                    .order_by('-is_builtin_map', 'name'))
        return queryset


class PopularServersViewSet(ListModelMixin, GenericViewSet):
    serializer_class = ServerBaseSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = (Server.objects
                    .annotate(game_num=Count('game'))
                    .filter(game_num__gt=0)
                    .order_by('-game_num', 'hostname', 'pk'))
        return queryset


class ServerLeaderboardViewSet(ListModelMixin, GenericViewSet):
    queryset = ServerStats.objects.all()
    serializer_class = PlayerStatSerializer
    pagination_class = paginator_factory(page_size=20, ordering=('position', 'id'))

    def get_queryset(self):
        return (ServerStats.objects
                .select_related('profile', 'profile__loadout')
                .filter(year=get_current_stat_year()))
