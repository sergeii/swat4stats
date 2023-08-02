from datetime import datetime
from functools import partial

import pytest
import pytz
from django.core.management import call_command
from django.utils import timezone

from apps.tracker.factories import ProfileFactory, PlayerFactory, RandomLoadoutFactory
from apps.utils.test import freeze_timezone_now

utc_datetime = partial(datetime, tzinfo=pytz.utc)


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_preferences(db, settings, django_assert_num_queries):
    settings.TRACKER_PREFERRED_GAMES = 3

    now = timezone.now()

    lo1, lo2, lo3 = RandomLoadoutFactory.create_batch(3)

    no_stats_profile = ProfileFactory()
    profile1 = ProfileFactory(
        first_seen_at=utc_datetime(2008, 1, 1, 1, 1, 1),
        last_seen_at=utc_datetime(2012, 2, 2, 2, 2, 2),
    )
    profile2 = ProfileFactory(
        first_seen_at=utc_datetime(2014, 4, 4, 4, 4, 4),
        last_seen_at=utc_datetime(2019, 9, 9, 9, 9, 9),
    )

    PlayerFactory(
        alias__profile=profile1,
        alias__name="Player<AFK>",
        alias__isp__country="US",
        loadout=lo1,
        team="suspects",
    )
    PlayerFactory(
        alias__profile=profile1,
        alias__name="Player",
        alias__isp__country="CA",
        loadout=lo1,
        team="swat",
    )
    PlayerFactory(
        alias__profile=profile1,
        alias__name="Player",
        alias__isp__country="US",
        loadout=lo2,
        team="swat",
    )

    PlayerFactory(
        alias__profile=profile2,
        alias__name="Jogador",
        alias__isp__country="EU",
        loadout=lo1,
        team="suspects",
    )
    PlayerFactory(
        alias__profile=profile2,
        alias__name="Jugador",
        alias__isp__country="CY",
        loadout=lo3,
        team="swat",
    )
    PlayerFactory(
        alias__profile=profile2,
        alias__name="Jogador",
        alias__isp__country="CY",
        loadout=lo2,
        team="suspects",
    )
    PlayerFactory(
        alias__profile=profile2,
        alias__name="Jogador",
        alias__isp__country="CY",
        loadout=lo3,
        team="suspects",
    )

    for p in [no_stats_profile, profile1, profile2]:
        assert p.team is None
        assert p.team_legacy is None
        assert p.country is None
        assert p.loadout is None
        assert p.stats_updated_at is None
        assert p.preferences_updated_at is None

    with freeze_timezone_now(now), django_assert_num_queries(15):
        call_command("fill_preferences")

    for p in [no_stats_profile, profile1, profile2]:
        p.refresh_from_db()

    assert no_stats_profile.preferences_updated_at is None
    assert profile1.preferences_updated_at == now
    assert profile2.preferences_updated_at == now

    assert no_stats_profile.name is None
    assert no_stats_profile.team is None
    assert no_stats_profile.team_legacy is None
    assert no_stats_profile.country is None
    assert no_stats_profile.loadout is None

    assert profile1.name == "Player"
    assert profile1.country == "US"
    assert profile1.team == "swat"
    assert profile1.team_legacy == 0
    assert profile1.loadout == lo1

    assert profile2.name == "Jogador"
    assert profile2.country == "CY"
    assert profile2.team == "suspects"
    assert profile2.team_legacy == 1
    assert profile2.loadout == lo3
