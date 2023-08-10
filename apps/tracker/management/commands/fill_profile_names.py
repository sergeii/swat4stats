import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Model

from apps.utils.misc import iterate_list

logger = logging.getLogger(__name__)


def fill_profile_names(profile_model: type[Model]) -> None:
    profiles_with_ids = list(profile_model.objects.using("replica").values_list("pk", flat=True))
    for profile_ids in iterate_list(profiles_with_ids, size=1000):
        profile_model.objects.denorm_alias_names(*profile_ids)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.tracker.models import Profile

        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_profile_names(Profile)
