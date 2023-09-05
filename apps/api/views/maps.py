from django.db.models import QuerySet
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from apps.api.serializers import MapSerializer
from apps.tracker.models import Map


class PopularMapsViewSet(ListModelMixin, GenericViewSet):
    serializer_class = MapSerializer
    pagination_class = None

    max_maps = 100

    def get_queryset(self) -> QuerySet[Map]:
        qs = Map.objects.filter(rating__isnull=False).order_by("rating", "-game_count")
        return qs[: self.max_maps]
