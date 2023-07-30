from django.db.models import QuerySet
from rest_framework.generics import ListAPIView

from apps.api.filters import SearchFilterSet, SearchFilterBackend
from apps.api.pagination import limit_offset_pagination_factory
from apps.api.serializers import ProfileSerializer
from apps.tracker.models import Profile


class SearchView(ListAPIView):
    serializer_class = ProfileSerializer
    pagination_class = limit_offset_pagination_factory(default_limit=20, max_limit=100)
    filter_backends = (SearchFilterBackend,)
    filterset_class = SearchFilterSet

    def get_queryset(self) -> QuerySet[Profile]:
        return (
            Profile.objects
            .select_related('loadout')
            .filter(last_seen_at__isnull=False)
        )
