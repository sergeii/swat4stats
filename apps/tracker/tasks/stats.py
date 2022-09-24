import random
import logging

from django.conf import settings
from django.utils import timezone

from swat4stats.celery import app
from apps.tracker.models import Profile, PlayerStats, ServerStats, GametypeStats

__all__ = [
    'update_player_stats',
    'update_player_stats_for_profile',
    'update_player_positions',
    'settle_annual_player_positions'
]

logger = logging.getLogger(__name__)


@app.task(name='update_player_stats')
def update_player_stats():
    """
    Queue stats update tasks for players that have played past the latest stats update time.
    """
    cnt = 0
    queryset = Profile.objects.require_stats_update()
    for profile in queryset.only('pk'):
        cnt += 1
        update_player_stats_for_profile.apply_async(args=(profile.pk,),
                                                    countdown=random.randint(5, 600))
    if cnt:
        logger.info('updating stats for %s profiles', cnt)


@app.task
def update_player_stats_for_profile(profile_pk):
    profile = Profile.objects.get(pk=profile_pk)
    logger.info('updating stats for profile %s', profile_pk)
    profile.update_stats()
    logger.info('finished updating stats for profile %s', profile_pk)


@app.task(name='update_player_positions')
def update_player_positions():
    """
    Update leaderboards' positions for a period of the current year
    """
    now = timezone.now()
    update_player_positions_for_year(now.year)


@app.task(name='settle_annual_player_positions')
def settle_annual_player_positions():
    """
    Update leaderboards' positions for completed year
    """
    now = timezone.now()
    update_player_positions_for_year(now.year - 1)


def update_player_positions_for_year(year: int) -> None:
    logger.info('updating player positions for %s', year)

    # global player stats
    PlayerStats.objects.rank(year=year, cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME})
    PlayerStats.objects.rank(year=year, cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES})
    PlayerStats.objects.rank(year=year, cats=['kd_ratio'], qualify={'kills': settings.TRACKER_MIN_KILLS})
    PlayerStats.objects.rank(year=year,
                             cats=['weapon_hit_ratio', 'weapon_kill_ratio'],
                             qualify={'weapon_shots': settings.TRACKER_MIN_WEAPON_SHOTS})
    PlayerStats.objects.rank(year=year,
                             cats=['grenade_hit_ratio'],
                             qualify={'grenade_shots': settings.TRACKER_MIN_GRENADE_SHOTS})
    PlayerStats.objects.rank(year=year,
                             exclude_cats=['spm_ratio', 'spr_ratio', 'kd_ratio',
                                           'weapon_hit_ratio', 'weapon_kill_ratio', 'grenade_hit_ratio',
                                           'weapon_teamhit_ratio', 'grenade_teamhit_ratio'])

    # per gametype player stats
    GametypeStats.objects.rank(year=year, cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME})
    GametypeStats.objects.rank(year=year, cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES})
    GametypeStats.objects.rank(year=year, exclude_cats=['spm_ratio', 'spr_ratio'])

    # per server player stats
    ServerStats.objects.rank(year=year, cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME})
    ServerStats.objects.rank(year=year, cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES})
    ServerStats.objects.rank(year=year, cats=['kd_ratio'], qualify={'kills': settings.TRACKER_MIN_KILLS})
    ServerStats.objects.rank(year=year, exclude_cats=['spm_ratio', 'spr_ratio', 'kd_ratio'])

    logger.info('finished updating player positions for %s', year)
