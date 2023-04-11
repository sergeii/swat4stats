import random
import logging

from django.db import transaction

from swat4stats.celery import app
from apps.tracker.models import Profile


__all__ = [
    'update_player_preferences',
    'update_player_preferences_for_profile',
]


logger = logging.getLogger(__name__)


@app.task(name='update_player_preferences')
def update_player_preferences() -> None:
    """
    Update preferences such as name, country, loadout, etc
    for players recently seen playing.
    """
    queryset = Profile.objects.require_preference_update()
    for profile in queryset.only('pk'):
        logger.info('profile %s requires preference update', profile.pk)
        update_player_preferences_for_profile.apply_async(args=(profile.pk,),
                                                          countdown=random.randint(30, 300))


@app.task
@transaction.atomic
def update_player_preferences_for_profile(profile_pk: int) -> None:
    """Update preferences for given profile"""
    profile = Profile.objects.get(pk=profile_pk)
    logger.info('updating preferences for %s', profile)
    profile.update_preferences()
