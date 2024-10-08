import logging
import random

from apps.tracker.models import Profile
from apps.utils.misc import iterate_queryset
from swat4stats.celery import Queue, app

__all__ = [
    "denorm_profile_names",
    "update_player_preferences",
    "update_player_preferences_for_profile",
]


logger = logging.getLogger(__name__)


@app.task(name="update_player_preferences", queue=Queue.default.value)
def update_player_preferences() -> None:
    """
    Update preferences such as name, country, loadout, etc.
    for players recently seen playing.
    """
    queryset = Profile.objects.require_preference_update()
    for profile in queryset.only("pk"):
        logger.info("profile %s requires preference update", profile.pk)
        update_player_preferences_for_profile.apply_async(
            args=(profile.pk,), countdown=random.randint(30, 300)
        )


@app.task(queue=Queue.default.value)
def update_player_preferences_for_profile(profile_pk: int) -> None:
    """Update preferences for given profile"""
    profile = Profile.objects.get(pk=profile_pk)
    logger.info("updating preferences for %s", profile)
    Profile.objects.update_preferences_for_profile(profile)


@app.task(name="denorm_profile_names", queue=Queue.default.value)
def denorm_profile_names(chunk_size: int = 1000) -> None:
    profiles_with_ids = Profile.objects.require_denorm_names().using("replica")
    for chunk in iterate_queryset(profiles_with_ids, fields=["pk"], chunk_size=chunk_size):
        profile_ids = [profile["pk"] for profile in chunk]
        Profile.objects.denorm_alias_names(*profile_ids)
