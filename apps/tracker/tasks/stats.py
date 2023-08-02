import random
import logging

from django.utils import timezone

from swat4stats.celery import app, Queue
from apps.tracker.models import Profile

__all__ = [
    "update_player_stats",
    "update_player_stats_for_profile",
    "update_player_positions",
    "settle_annual_player_positions",
]

logger = logging.getLogger(__name__)


@app.task(name="update_player_stats", queue=Queue.default.value)
def update_player_stats() -> None:
    """
    Queue stats update tasks for players that have played past the latest stats update time.
    """
    cnt = 0
    queryset = Profile.objects.require_stats_update()
    for profile in queryset.only("pk"):
        cnt += 1
        update_player_stats_for_profile.apply_async(
            args=(profile.pk,), countdown=random.randint(5, 600)
        )
    if cnt:
        logger.info("updating stats for %s profiles", cnt)


@app.task(queue=Queue.default.value)
def update_player_stats_for_profile(profile_id: int) -> None:
    profile = Profile.objects.get(pk=profile_id)
    logger.info("updating stats for profile (%s) %s", profile_id, profile)
    Profile.objects.update_stats_for_profile(profile)
    logger.info("finished updating stats for profile %s (%s)", profile_id, profile)


@app.task(name="update_player_positions", queue=Queue.default.value)
def update_player_positions() -> None:
    """
    Update leaderboards' positions for a period of the current year
    """
    now = timezone.now()
    Profile.objects.update_player_positions_for_year(now.year)


@app.task(name="settle_annual_player_positions", queue=Queue.default.value)
def settle_annual_player_positions() -> None:
    """
    Update leaderboards' positions for completed year
    """
    now = timezone.now()
    Profile.objects.update_player_positions_for_year(now.year - 1)
