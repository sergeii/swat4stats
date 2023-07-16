import logging

from django.core.management.base import BaseCommand
from django.db.models import Model


logger = logging.getLogger(__name__)


def fill_alias_denorm_fields(alias_model: type[Model]):
    queryset = (alias_model.objects
                .only('profile_name', 'isp_name', 'isp_country',
                      'profile__name', 'isp__name', 'isp__country')
                .select_related('profile', 'isp'))

    logger.info('updating denorm fields for %s aliases', queryset.count())

    for alias in queryset:
        alias.profile_name = alias.profile.name
        alias.isp_name = alias.isp.name if alias.isp else None
        alias.isp_country = alias.isp.country if alias.isp else None

        logger.info('setting profile_name=%s isp_name=%s isp_country=%s for alias %s',
                    alias.profile_name, alias.isp_name, alias.isp_country, alias.pk)

    alias_model.objects.bulk_update(queryset, fields=['profile_name', 'isp_name', 'isp_country'], batch_size=100)


class Command(BaseCommand):

    def handle(self, *args, **options):
        from apps.tracker.models import Alias

        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_alias_denorm_fields(Alias)
