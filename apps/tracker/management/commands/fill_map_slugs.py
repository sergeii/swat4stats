import logging

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.tracker.models import Map
from apps.utils.misc import iterate_list

logger = logging.getLogger(__name__)


def fill_map_slugs() -> None:
    maps_with_ids = list(
        Map.objects.using("replica").filter(slug__isnull=True).values_list("pk", flat=True)
    )
    for map_ids in iterate_list(maps_with_ids, size=1000):
        maps_to_update = Map.objects.filter(pk__in=map_ids, slug__isnull=True)
        for map_to_update in maps_to_update:
            map_to_update.slug = slugify(map_to_update.name)
        Map.objects.bulk_update(maps_to_update, ["slug"])


class Command(BaseCommand):
    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_map_slugs()
