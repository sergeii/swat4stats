import logging

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from apps.tracker.models import Profile, PlayerStats, GametypeStats, ServerStats
from apps.tracker.utils.misc import iterate_years

logger = logging.getLogger(__name__)


def fill_profile_stats(queryset: QuerySet[Profile]) -> None:
    logger.info("updating stats for %s profiles", queryset.count())

    for year_date in iterate_years(date(2007, 1, 1), timezone.now().date()):
        year = year_date.year
        for profile in queryset.iterator():
            Profile.objects.update_annual_stats_for_profile(profile=profile, year=year)

    queryset.update(stats_updated_at=timezone.now())


def calculate_positions() -> None:
    for year_date in iterate_years(date(2007, 1, 1), timezone.now().date()):
        year = year_date.year
        for model in [PlayerStats, GametypeStats, ServerStats]:
            logger.info("updating positions for %s %s", year, model.__name__)
            model.objects.rank(year=year)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        console = logging.StreamHandler()
        logger.addHandler(console)

        queryset = Profile.objects.all()
        fill_profile_stats(queryset)
        calculate_positions()
