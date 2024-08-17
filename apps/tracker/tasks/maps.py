import logging

from django.conf import settings

from apps.tracker.models import Map
from swat4stats.celery import Queue, app

__all__ = [
    "update_map_details",
    "update_map_ratings",
]

logger = logging.getLogger(__name__)


@app.task(name="update_map_details", queue=Queue.default.value)
def update_map_details() -> None:
    if release_sha := settings.GIT_RELEASE_SHA:
        Map.objects.update_details(version=release_sha)
    else:
        logger.error("update_map_details: No GIT_RELEASE_SHA found in settings")


@app.task(name="update_map_ratings", queue=Queue.default.value)
def update_map_ratings() -> None:
    Map.objects.update_ratings()
