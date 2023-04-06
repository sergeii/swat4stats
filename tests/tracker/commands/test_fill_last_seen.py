from datetime import datetime
from functools import partial

import pytz
from django.core.management import call_command

from apps.tracker.factories import ProfileFactory, GameFactory

utc_datetime = partial(datetime, tzinfo=pytz.utc)


def test_fill_last_seen(db, django_assert_num_queries):
    game1 = GameFactory(date_finished=utc_datetime(2016, 3, 14, 1, 1, 1))
    game2 = GameFactory(date_finished=utc_datetime(2017, 12, 31, 1, 1, 1))
    # no games, no dates
    profile1 = ProfileFactory(first_seen_at=None, last_seen_at=None)
    # no dates, have same first and last game
    profile2 = ProfileFactory(first_seen_at=None, last_seen_at=None,
                              game_first=game1, game_last=game1)
    # no dates, have different first and last game
    profile3 = ProfileFactory(first_seen_at=None, last_seen_at=None,
                              game_first=game1, game_last=game2)
    # no dates, have last game
    profile4 = ProfileFactory(first_seen_at=None, last_seen_at=None,
                              game_last__date_finished=utc_datetime(2018, 2, 15, 1, 1, 1))
    # have dates, have games, dates differ from games
    profile5 = ProfileFactory(first_seen_at=utc_datetime(2007, 5, 14, 1, 1, 1),
                              last_seen_at=utc_datetime(2019, 2, 15, 1, 1, 1),
                              game_first__date_finished=utc_datetime(2008, 11, 1, 1, 1, 1),
                              game_last__date_finished=utc_datetime(2020, 5, 8, 1, 1, 1))

    with django_assert_num_queries(3):
        call_command('fill_last_seen')

    for p in [profile1, profile2, profile4, profile5]:
        p.refresh_from_db()

    assert profile1.first_seen_at is None
    assert profile1.last_seen_at is None

    assert profile2.first_seen_at == utc_datetime(2016, 3, 14, 1, 1, 1)
    assert profile2.last_seen_at == utc_datetime(2016, 3, 14, 1, 1, 1)

    assert profile3.first_seen_at == utc_datetime(2016, 3, 14, 1, 1, 1)
    assert profile3.last_seen_at == utc_datetime(2017, 12, 31, 1, 1, 1)

    assert profile4.first_seen_at is None
    assert profile4.last_seen_at == utc_datetime(2018, 2, 15, 1, 1, 1)

    assert profile5.first_seen_at == utc_datetime(2007, 5, 14, 1, 1, 1)
    assert profile5.last_seen_at == utc_datetime(2019, 2, 15, 1, 1, 1)
