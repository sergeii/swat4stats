from datetime import datetime
from functools import partial

import pytest
import pytz
from django.core.management import call_command
from django.utils import timezone

from apps.tracker.factories import ProfileFactory, MapFactory, PlayerFactory
from apps.tracker.models import PlayerStats, GametypeStats, MapStats, ServerStats
from apps.utils.test import freeze_timezone_now

utc_datetime = partial(datetime, tzinfo=pytz.utc)


@pytest.mark.django_db(databases=['default', 'replica'])
def test_fill_stats(db, settings):
    settings.TRACKER_MIN_TIME = 0
    settings.TRACKER_MIN_GAMES = 1

    now = timezone.now()

    abomb = MapFactory(name='A-Bomb Nightclub')
    brewer = MapFactory(name='Brewer County Courthouse')

    no_stats_profile = ProfileFactory()
    profile1 = ProfileFactory(first_seen_at=utc_datetime(2008, 1, 1, 1, 1, 1),
                              last_seen_at=utc_datetime(2012, 2, 2, 2, 2, 2))
    profile2 = ProfileFactory(first_seen_at=utc_datetime(2014, 4, 4, 4, 4, 4),
                              last_seen_at=utc_datetime(2019, 9, 9, 9, 9, 9))

    PlayerFactory(alias__profile=profile1,
                  alias__isp__country='US',
                  game__date_finished=utc_datetime(2008, 1, 1, 1, 1, 1),
                  game__map=abomb,
                  game__gametype='VIP Escort',
                  team='suspects',
                  score=192,
                  time=200)
    PlayerFactory(alias__profile=profile1,
                  game__date_finished=utc_datetime(2008, 1, 2, 1, 1, 1),
                  game__map=abomb,
                  game__gametype='VIP Escort',
                  score=20,
                  time=50)
    PlayerFactory(alias__profile=profile1,
                  game__date_finished=utc_datetime(2012, 2, 2, 2, 2, 2),
                  game__map=brewer,
                  game__gametype='VIP Escort',
                  score=20,
                  time=50)

    PlayerFactory(alias__profile=profile2,
                  game__date_finished=utc_datetime(2014, 4, 4, 4, 4, 4),
                  game__map=brewer,
                  game__gametype='VIP Escort',
                  time=1337,
                  score=42)
    PlayerFactory(alias__profile=profile2,
                  game__date_finished=utc_datetime(2015, 5, 5, 5, 5, 5),
                  game__map=brewer,
                  game__gametype='VIP Escort',
                  time=900,
                  score=1)
    PlayerFactory(alias__profile=profile2,
                  game__date_finished=utc_datetime(2018, 8, 8, 8, 8, 8),
                  game__map=brewer,
                  game__gametype='Barricaded Suspects',
                  time=50,
                  score=18)
    PlayerFactory(alias__profile=profile2,
                  game__date_finished=utc_datetime(2019, 9, 9, 9, 9, 9),
                  game__map=brewer,
                  game__gametype='Rapid Deployment',
                  time=10,
                  score=25)

    for p in [no_stats_profile, profile1, profile2]:
        assert p.stats_updated_at is None

    with freeze_timezone_now(now):
        call_command('fill_stats')

    for p in [no_stats_profile, profile1, profile2]:
        p.refresh_from_db()
        assert p.stats_updated_at == now

    for model in [PlayerStats, GametypeStats, MapStats, ServerStats]:
        profile1_years = set(model.objects.filter(profile=profile1).values_list('year', flat=True))
        assert profile1_years == {2008, 2012}
        profile2_years = set(model.objects.filter(profile=profile2).values_list('year', flat=True))
        assert profile2_years == {2014, 2015, 2018, 2019}

    for model in [PlayerStats, GametypeStats, ServerStats]:
        profile1_positions = set(model.objects.filter(profile=profile1).values_list('position', flat=True))
        assert profile1_positions == {1}
        profile2_positions = set(model.objects.filter(profile=profile2).values_list('position', flat=True))
        assert profile2_positions == {1}
