import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.tracker.models import Map
from apps.utils.misc import iterate_list

logger = logging.getLogger(__name__)


def fill_map_stats() -> None:
    maps_with_ids = list(
        Map.objects.using("replica")
        .filter(Q(first_game__isnull=True) | Q(latest_game__isnull=True))
        .values_list("pk", flat=True)
    )
    for map_ids in iterate_list(maps_with_ids, size=1000):
        maps_to_update = Map.objects.filter(pk__in=map_ids)
        Map.objects.denorm_game_stats(*maps_to_update)


class Command(BaseCommand):
    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_map_stats()
