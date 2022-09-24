import logging

from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tracker.models import Profile, PlayerStats, GametypeStats
from apps.tracker.utils import iterate_years

logger = logging.getLogger(__name__)


def fill_profile_stats(queryset):
    logger.info('updating %s profiles', queryset.count())

    for profile in queryset:
        logger.info('updating preferences for %s (%s)', profile, profile.pk)
        profile.update_preferences()

    for year in iterate_years(date(2007, 1, 1), timezone.now().date()):
        for profile in queryset:
            logger.info('updating %s stats for %s (%s)', year, profile, profile.pk)
            profile.update_annual_stats(year=year)

    queryset.update(stats_updated_at=timezone.now())


def calculate_positions():
    for year in iterate_years(date(2007, 1, 1), timezone.now().date()):
        for model in [PlayerStats, GametypeStats]:
            logger.info('updating positions for %s %s', year, model.__name__)
            model.objects.rank(year=year)


class Command(BaseCommand):

    def handle(self, *args, **options):
        queryset = Profile.objects.all()
        fill_profile_stats(queryset)
        calculate_positions()
