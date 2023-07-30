import logging

from django.contrib.postgres.expressions import ArraySubquery
from django.core.management.base import BaseCommand
from django.db.models import Model, OuterRef

from apps.tracker.models import Alias
from apps.utils.misc import iterate_list

logger = logging.getLogger(__name__)


def fill_profile_names(profile_model: type[Model]):
    sub = (
        Alias.objects
        .filter(profile_id=OuterRef("pk"))
        .values_list("name")
    )
    profile_names = list(
        profile_model.objects
        .annotate(alias_names=ArraySubquery(sub))
        .values('pk', 'alias_names')
    )

    logger.info('updating denorm fields for %s profiles', len(profile_names))

    for chunk in iterate_list(profile_names, size=1000):
        name_per_profile = {
            item['pk']: item['alias_names']
            for item in chunk
        }
        chunk_qs = (profile_model.objects
                    .select_related(None)
                    .filter(pk__in=name_per_profile)
                    .only('pk', 'name'))
        for profile in chunk_qs:
            names = [
                name for name in name_per_profile[profile.pk]
                if name != profile.name
            ]
            profile.names = names

        profile_model.objects.bulk_update(chunk_qs, ['names'])


class Command(BaseCommand):

    def handle(self, *args, **options):
        from apps.tracker.models import Profile

        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_profile_names(Profile)
