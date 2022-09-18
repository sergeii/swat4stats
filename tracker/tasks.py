import logging

from django.db import transaction
from django.utils import timezone

from swat4tracker.celery import app
from tracker import models, utils


logger = logging.getLogger(__name__)


@app.task()
def update_popular(time_delta):
    """
    Update the profile popular fields such as name, country, loadout, etc
    that belong to players who have played just now or ``time_delta`` ago.

    Args:
        time_delta - time in past relative to the current time (seconds/timedelta obj)
    """
    min_date = timezone.now() - utils.force_timedelta(time_delta)

    queryset = (
        models.Profile.objects
        .select_for_update()
        .select_related('game_last')
        .filter(game_last__date_finished__gte=min_date)
    )

    with transaction.atomic():
        # update the popular fields
        for profile in queryset:
            profile.update_popular()
            profile.save()


@app.task()
def update_ranks(time_delta):
    """
    Update Rank entries that belong to players who have played just now or ``time_delta`` ago.

    Args:
        time_delta - time in past relative to the current time (seconds/timedelta obj)
    """
    min_date = timezone.now() - utils.force_timedelta(time_delta)

    queryset = (
        models.Profile.objects
        .popular()
        .select_related('game_last')
        .filter(game_last__date_finished__gte=min_date)
    )

    for profile in queryset:
        # aggregate stats relative to the last game's date
        year = profile.last_seen.year
        period = models.Rank.get_period_for_year(year)

        with transaction.atomic():
            # aggregate stats for the specified period
            stats = profile.aggregate_mode_stats(models.Profile.SET_STATS_ALL, *period)
            models.Rank.objects.store_many(stats, year, profile)


@app.task()
def update_positions(*args):
    """
    Rank up year specific leaderboards.

    Args:
        *args - years
        A zero or a negative value is considered a relative year to the current year
        Suppose 2014 is the current year, then 0 is 2014, -1 is 2013 and so on
    """
    years = []
    current_year = timezone.now().year

    for arg in args:
        # relative to the current year (0, -1, -2)
        if arg <= 0:
            years.append(arg + current_year)
        # year as is (2013, 2014, 2015)
        else:
            years.append(arg)

    # use the current year as fallback
    if not years:
        years.append(current_year)

    # rank up all leaderboard entries for every listed year
    for year in years:
        models.Rank.objects.rank(year)
