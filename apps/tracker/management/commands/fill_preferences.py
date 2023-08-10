import logging
from typing import Any

from django.core.management.base import BaseCommand

from apps.tracker.models import Profile

logger = logging.getLogger(__name__)


def fill_preferences() -> None:
    queryset = Profile.objects.all()

    logger.info("updating preferences for %s profiles", queryset.count())

    for profile in queryset.iterator():
        logger.info("updating preferences for %s (%s)", profile, profile.pk)
        Profile.objects.update_preferences_for_profile(profile)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_preferences()
