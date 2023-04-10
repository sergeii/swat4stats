import logging

from django.core.management.base import BaseCommand

from apps.tracker.models import Profile

logger = logging.getLogger(__name__)


def fill_preferences(queryset):
    logger.info('updating preferences for %s profiles', queryset.count())

    for profile in queryset:
        logger.info('updating preferences for %s (%s)', profile, profile.pk)
        profile.update_preferences()


class Command(BaseCommand):

    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)

        queryset = Profile.objects.all()
        fill_preferences(queryset)
