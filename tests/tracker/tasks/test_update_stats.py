from datetime import datetime, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils import timezone
from pytz import UTC

from apps.tracker.models import GametypeStats, MapStats, PlayerStats
from apps.tracker.tasks import update_player_stats
from tests.factories.stats import GametypeStatsFactory, PlayerStatsFactory
from tests.factories.tracker import (
    MapFactory,
    PlayerFactory,
    ProfileFactory,
)


@pytest.fixture
def abomb(db):
    return MapFactory(name="A-Bomb Nightclub")


@pytest.fixture
def brewer(db):
    return MapFactory(name="Brewer County Courthouse")


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_player_stats(db, abomb, brewer, django_assert_num_queries):
    now = timezone.now()
    then = datetime(2022, 10, 1, 10, 17, 1, tzinfo=UTC)

    profile1 = ProfileFactory(
        first_seen_at=then - timedelta(days=400),
        last_seen_at=then - timedelta(days=3),
        stats_updated_at=then - timedelta(days=4),
    )
    PlayerFactory(
        alias__profile=profile1,
        game__date_finished=then - timedelta(days=3),
        game__map=abomb,
        game__gametype="VIP Escort",
        score=192,
        time=200,
    )
    PlayerFactory(
        alias__profile=profile1,
        game__date_finished=then - timedelta(days=2),
        game__map=brewer,
        game__gametype="VIP Escort",
        score=20,
        time=50,
    )
    PlayerStatsFactory(profile=profile1, year=2021, category="time", points=1510, position=1)
    PlayerStatsFactory(profile=profile1, year=2022, category="time", points=200, position=1)
    PlayerStatsFactory(profile=profile1, year=2022, category="score", points=192, position=18)
    GametypeStatsFactory(
        profile=profile1, gametype="VIP Escort", year=2022, category="score", points=1
    )

    profile2 = ProfileFactory(
        first_seen_at=then - timedelta(days=90),
        last_seen_at=then - timedelta(days=3),
        stats_updated_at=None,
    )
    PlayerFactory(
        alias__profile=profile2,
        game__date_finished=then - relativedelta(years=1),
        game__map=brewer,
        game__gametype="VIP Escort",
        time=1337,
        score=42,
    )
    PlayerFactory(
        alias__profile=profile2,
        game__date_finished=then - timedelta(days=2),
        game__map=abomb,
        game__gametype="Barricaded Suspects",
        time=50,
        score=18,
    )
    PlayerFactory(
        alias__profile=profile2,
        game__date_finished=then - timedelta(days=1),
        game__map=abomb,
        game__gametype="Rapid Deployment",
        time=10,
        score=25,
    )

    with django_assert_num_queries(35):
        update_player_stats.delay()

    profile1.refresh_from_db()
    assert profile1.stats_updated_at >= now
    assert PlayerStats.objects.get(year=2022, profile=profile1, category="score").points == 212
    assert PlayerStats.objects.get(year=2022, profile=profile1, category="score").position == 18
    assert PlayerStats.objects.get(year=2022, profile=profile1, category="time").points == 250
    assert PlayerStats.objects.get(year=2022, profile=profile1, category="time").position == 1
    assert PlayerStats.objects.get(year=2021, profile=profile1, category="time").points == 1510
    assert PlayerStats.objects.get(year=2021, profile=profile1, category="time").position == 1
    assert PlayerStats.objects.filter(~Q(year__in=[2021, 2022]), profile=profile1).count() == 0

    assert (
        MapStats.objects.get(year=2022, profile=profile1, map=abomb, category="score").points == 192
    )
    assert (
        MapStats.objects.get(year=2022, profile=profile1, map=brewer, category="score").points == 20
    )
    assert MapStats.objects.filter(~Q(year=2022), profile=profile1).count() == 0

    assert (
        GametypeStats.objects.get(
            year=2022, profile=profile1, gametype="VIP Escort", category="score"
        ).points
        == 212
    )
    assert GametypeStats.objects.filter(~Q(year=2022), profile=profile1).count() == 0

    profile2.refresh_from_db()
    assert profile2.stats_updated_at >= now
    assert PlayerStats.objects.get(year=2022, profile=profile2, category="score").points == 43
    assert PlayerStats.objects.get(year=2022, profile=profile2, category="score").position is None
    assert PlayerStats.objects.get(year=2022, profile=profile2, category="time").points == 60
    assert PlayerStats.objects.get(year=2022, profile=profile2, category="time").position is None
    assert PlayerStats.objects.filter(~Q(year=2022), profile=profile2).count() == 0

    assert (
        MapStats.objects.get(year=2022, profile=profile2, map=abomb, category="score").points == 43
    )
    assert MapStats.objects.filter(profile=profile2, map=brewer).count() == 0
    assert MapStats.objects.filter(~Q(year=2022), profile=profile2).count() == 0

    assert (
        GametypeStats.objects.get(
            year=2022, profile=profile2, gametype="Barricaded Suspects", category="score"
        ).points
        == 18
    )
    assert (
        GametypeStats.objects.get(
            year=2022, profile=profile2, gametype="Rapid Deployment", category="score"
        ).points
        == 25
    )
    assert (
        GametypeStats.objects.filter(
            ~Q(gametype__in=["Barricaded Suspects", "Rapid Deployment"]),
            year=2022,
            profile=profile2,
        ).count()
        == 0
    )
    assert GametypeStats.objects.filter(~Q(year=2022), profile=profile2).count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_player_stats_no_updates(db):
    now = timezone.now()
    then = datetime(2022, 10, 1, 10, 17, 1, tzinfo=UTC)

    no_games_profile = ProfileFactory()

    emptied_profile = ProfileFactory(
        first_seen_at=datetime(2019, 1, 19, tzinfo=UTC),
        last_seen_at=datetime(2022, 8, 29, tzinfo=UTC),
        stats_updated_at=then - timedelta(days=3),
    )
    PlayerFactory(
        alias__profile=emptied_profile,
        game__date_finished=datetime(2020, 11, 3, tzinfo=UTC),
        common=True,
    )

    not_updated_emptied_profile = ProfileFactory(
        first_seen_at=then - timedelta(days=13), last_seen_at=then - timedelta(days=1)
    )

    updated_profile = ProfileFactory(
        first_seen_at=then - timedelta(days=7),
        last_seen_at=then - timedelta(days=3),
        stats_updated_at=then - timedelta(days=1),
    )
    PlayerFactory(alias__profile=updated_profile, game__date_finished=then, common=True)

    update_player_stats.delay()

    no_games_profile.refresh_from_db()
    assert no_games_profile.stats_updated_at is None

    emptied_profile.refresh_from_db()
    assert emptied_profile.stats_updated_at >= then - timedelta(days=3)

    not_updated_emptied_profile.refresh_from_db()
    assert not_updated_emptied_profile.stats_updated_at >= now

    updated_profile.refresh_from_db()
    assert updated_profile.stats_updated_at == then - timedelta(days=1)

    assert PlayerStats.objects.count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_player_stats_for_last_played_year(db):
    now = timezone.now()

    old_profile = ProfileFactory(
        first_seen_at=datetime(2008, 1, 3, 15, 19, 12, tzinfo=UTC),
        last_seen_at=datetime(2013, 1, 3, 15, 19, 12, tzinfo=UTC),
    )
    PlayerFactory(
        alias__profile=old_profile,
        game__date_finished=datetime(2011, 3, 13, 19, 10, 22, tzinfo=UTC),
        score=120,
    )
    PlayerFactory(
        alias__profile=old_profile,
        game__date_finished=datetime(2013, 1, 3, 15, 19, 12, tzinfo=UTC),
        score=99,
    )
    PlayerFactory(
        alias__profile=old_profile,
        game__date_finished=datetime(2013, 1, 4, 11, 1, 8, tzinfo=UTC),
        score=1,
    )

    recent_profile = ProfileFactory(
        first_seen_at=datetime(2012, 1, 3, 15, 19, 12, tzinfo=UTC),
        last_seen_at=datetime(2022, 10, 3, 22, 18, 13, tzinfo=UTC),
    )
    PlayerFactory(
        alias__profile=recent_profile,
        game__date_finished=datetime(2021, 8, 16, 18, 18, 31, tzinfo=UTC),
        kills=5,
    )
    PlayerStatsFactory(profile=recent_profile, year=2021, category="kills", points=3, position=99)
    PlayerFactory(
        alias__profile=recent_profile,
        game__date_finished=datetime(2022, 9, 30, 0, 16, 57, tzinfo=UTC),
        score=24,
        kills=19,
    )
    PlayerFactory(
        alias__profile=recent_profile,
        game__date_finished=datetime(2022, 10, 1, 15, 45, 1, tzinfo=UTC),
        score=5,
        kills=8,
    )
    PlayerStatsFactory(profile=recent_profile, year=2022, category="kills", points=19, position=3)

    update_player_stats.delay()

    old_profile.refresh_from_db()
    assert old_profile.stats_updated_at >= now
    assert PlayerStats.objects.filter(~Q(year=2013), profile=old_profile).count() == 0
    assert PlayerStats.objects.filter(year=2013, profile=old_profile).count() > 0
    assert PlayerStats.objects.get(year=2013, profile=old_profile, category="score").points == 100

    recent_profile.refresh_from_db()
    assert recent_profile.stats_updated_at >= now

    assert (
        PlayerStats.objects.filter(~Q(year__in=[2021, 2022]), profile=recent_profile).count() == 0
    )
    assert PlayerStats.objects.filter(year=2021, profile=recent_profile).count() > 0
    assert PlayerStats.objects.get(year=2021, profile=recent_profile, category="kills").points == 3
    assert (
        PlayerStats.objects.get(year=2021, profile=recent_profile, category="kills").position == 99
    )
    assert (
        PlayerStats.objects.filter(year=2021, profile=recent_profile, category="score").count() == 0
    )

    assert PlayerStats.objects.filter(year=2022, profile=recent_profile).count() > 0
    assert PlayerStats.objects.get(year=2022, profile=recent_profile, category="kills").points == 27
    assert (
        PlayerStats.objects.get(year=2022, profile=recent_profile, category="kills").position == 3
    )
    assert PlayerStats.objects.get(year=2022, profile=recent_profile, category="score").points == 29
    assert (
        PlayerStats.objects.get(year=2022, profile=recent_profile, category="score").position
        is None
    )
