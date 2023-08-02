import pytest
from django.utils import timezone

from apps.tracker.factories import (
    ProfileFactory,
    PlayerStatsFactory,
    ServerFactory,
    ServerStatsFactory,
    MapStatsFactory,
    GametypeStatsFactory,
)
from apps.tracker.models import PlayerStats, ServerStats, MapStats, GametypeStats, Profile


@pytest.fixture
def now():
    return timezone.now()


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_positions(settings, now):
    settings.TRACKER_MIN_TIME = 200
    settings.TRACKER_MIN_GAMES = 50
    settings.TRACKER_MIN_KILLS = 100
    settings.TRACKER_MIN_WEAPON_SHOTS = 1000
    settings.TRACKER_MIN_GRENADE_SHOTS = 50

    profile1, profile2, profile3 = ProfileFactory.create_batch(3)
    server1, server2 = ServerFactory.create_batch(2)

    PlayerStatsFactory(category="score", year=now.year, profile=profile1, points=1000, position=1)
    PlayerStatsFactory(category="score", year=now.year, profile=profile2, points=2000, position=2)
    PlayerStatsFactory(
        category="score", year=now.year, profile=profile3, points=3000, position=None
    )
    PlayerStatsFactory(category="time", year=now.year, profile=profile1, points=100, position=None)
    PlayerStatsFactory(category="time", year=now.year, profile=profile2, points=100, position=None)
    PlayerStatsFactory(category="time", year=now.year, profile=profile3, points=200, position=3)
    PlayerStatsFactory(category="games", year=now.year, profile=profile1, points=49, position=None)
    PlayerStatsFactory(category="games", year=now.year, profile=profile2, points=109, position=None)
    PlayerStatsFactory(category="games", year=now.year, profile=profile3, points=50, position=None)
    PlayerStatsFactory(category="kills", year=now.year, profile=profile1, points=100, position=None)
    PlayerStatsFactory(category="kills", year=now.year, profile=profile2, points=150, position=None)

    PlayerStatsFactory(
        category="spm_ratio", year=now.year, profile=profile1, points=1.5, position=1
    )
    PlayerStatsFactory(
        category="spm_ratio", year=now.year, profile=profile2, points=1.8, position=2
    )
    PlayerStatsFactory(
        category="spm_ratio", year=now.year, profile=profile3, points=1.1, position=3
    )
    PlayerStatsFactory(
        category="spr_ratio", year=now.year, profile=profile1, points=4.5, position=1
    )
    PlayerStatsFactory(
        category="spr_ratio", year=now.year, profile=profile2, points=1.8, position=2
    )
    PlayerStatsFactory(
        category="spr_ratio", year=now.year, profile=profile3, points=9.1, position=3
    )
    PlayerStatsFactory(category="kd_ratio", year=now.year, profile=profile1, points=3.5, position=2)
    PlayerStatsFactory(category="kd_ratio", year=now.year, profile=profile2, points=3.6, position=1)
    PlayerStatsFactory(category="kd_ratio", year=now.year, profile=profile3, points=5.8, position=3)

    PlayerStatsFactory(
        category="weapon_shots", year=now.year, profile=profile1, points=999, position=None
    )
    PlayerStatsFactory(
        category="weapon_shots", year=now.year, profile=profile2, points=1000, position=None
    )
    PlayerStatsFactory(
        category="weapon_shots", year=now.year, profile=profile3, points=1500, position=None
    )
    PlayerStatsFactory(
        category="weapon_hit_ratio", year=now.year, profile=profile1, points=10.5, position=None
    )
    PlayerStatsFactory(
        category="weapon_hit_ratio", year=now.year, profile=profile2, points=8.1, position=None
    )
    PlayerStatsFactory(
        category="weapon_kill_ratio", year=now.year, profile=profile1, points=1.5, position=None
    )
    PlayerStatsFactory(
        category="weapon_kill_ratio", year=now.year, profile=profile2, points=10.5, position=None
    )
    PlayerStatsFactory(
        category="weapon_kill_ratio", year=now.year, profile=profile3, points=8.1, position=None
    )
    PlayerStatsFactory(
        category="weapon_teamhit_ratio", year=now.year, profile=profile1, points=5.1, position=None
    )
    PlayerStatsFactory(
        category="weapon_teamhit_ratio", year=now.year, profile=profile2, points=1.5, position=None
    )
    PlayerStatsFactory(
        category="grenade_teamhit_ratio", year=now.year, profile=profile1, points=8.8, position=None
    )
    PlayerStatsFactory(
        category="grenade_teamhit_ratio",
        year=now.year,
        profile=profile2,
        points=15.1,
        position=None,
    )

    ServerStatsFactory(
        category="score", year=now.year, server=server1, profile=profile1, points=1, position=2
    )
    ServerStatsFactory(
        category="score", year=now.year, server=server2, profile=profile1, points=100, position=None
    )
    ServerStatsFactory(
        category="score", year=now.year, server=server2, profile=profile2, points=200, position=2
    )
    ServerStatsFactory(
        category="score", year=now.year, server=server2, profile=profile3, points=300, position=2
    )
    ServerStatsFactory(
        category="kills", year=now.year, server=server1, profile=profile1, points=178, position=None
    )
    ServerStatsFactory(
        category="kills", year=now.year, server=server1, profile=profile2, points=178, position=1
    )
    ServerStatsFactory(
        category="kills", year=now.year, server=server1, profile=profile3, points=99, position=2
    )
    ServerStatsFactory(
        category="kills", year=now.year, server=server2, profile=profile3, points=300, position=1
    )

    ServerStatsFactory(
        category="kd_ratio", year=now.year, server=server1, profile=profile1, points=1.1, position=2
    )
    ServerStatsFactory(
        category="kd_ratio",
        year=now.year,
        server=server1,
        profile=profile2,
        points=3.1,
        position=None,
    )
    ServerStatsFactory(
        category="kd_ratio", year=now.year, server=server1, profile=profile3, points=4.1, position=3
    )
    ServerStatsFactory(
        category="kd_ratio", year=now.year, server=server2, profile=profile1, points=1.5, position=2
    )
    ServerStatsFactory(
        category="kd_ratio",
        year=now.year,
        server=server2,
        profile=profile2,
        points=2.5,
        position=None,
    )
    ServerStatsFactory(
        category="kd_ratio", year=now.year, server=server2, profile=profile3, points=3.5, position=3
    )

    GametypeStatsFactory(
        category="arrests",
        gametype="VIP Escort",
        year=now.year,
        profile=profile1,
        points=10,
        position=2,
    )
    GametypeStatsFactory(
        category="arrests",
        gametype="VIP Escort",
        year=now.year,
        profile=profile3,
        points=10,
        position=None,
    )
    GametypeStatsFactory(
        category="arrests",
        gametype="VIP Escort",
        year=now.year,
        profile=profile2,
        points=11,
        position=None,
    )
    GametypeStatsFactory(
        category="time",
        gametype="VIP Escort",
        year=now.year,
        profile=profile1,
        points=600,
        position=None,
    )
    GametypeStatsFactory(
        category="time",
        gametype="VIP Escort",
        year=now.year,
        profile=profile2,
        points=50,
        position=None,
    )
    GametypeStatsFactory(
        category="spm_ratio",
        gametype="VIP Escort",
        year=now.year,
        profile=profile1,
        points=1.8,
        position=None,
    )
    GametypeStatsFactory(
        category="spm_ratio",
        gametype="VIP Escort",
        year=now.year,
        profile=profile2,
        points=1.5,
        position=2,
    )

    GametypeStatsFactory(
        category="arrests",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile1,
        points=10,
        position=None,
    )
    GametypeStatsFactory(
        category="time",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile1,
        points=60,
        position=2,
    )
    GametypeStatsFactory(
        category="time",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile2,
        points=600,
        position=None,
    )
    GametypeStatsFactory(
        category="games",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile2,
        points=50,
        position=None,
    )
    GametypeStatsFactory(
        category="spm_ratio",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile1,
        points=10.8,
        position=1,
    )
    GametypeStatsFactory(
        category="spm_ratio",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile2,
        points=1.3,
        position=None,
    )
    GametypeStatsFactory(
        category="spr_ratio",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile1,
        points=27.5,
        position=1,
    )
    GametypeStatsFactory(
        category="spr_ratio",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile2,
        points=27.1,
        position=2,
    )
    GametypeStatsFactory(
        category="score",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile1,
        points=18,
        position=2,
    )
    GametypeStatsFactory(
        category="score",
        gametype="Rapid Deployment",
        year=now.year,
        profile=profile2,
        points=17,
        position=1,
    )

    # should not be updated
    PlayerStatsFactory(
        category="score", year=now.year + 1, profile=profile1, points=10000, position=4
    )
    PlayerStatsFactory(
        category="score", year=now.year - 1, profile=profile2, points=10000, position=None
    )
    ServerStatsFactory(
        category="time",
        year=now.year - 1,
        server=server2,
        profile=profile2,
        points=100,
        position=None,
    )
    MapStatsFactory(category="time", year=now.year, profile=profile1, points=100, position=None)
    GametypeStatsFactory(
        category="time",
        gametype="VIP Escort",
        year=now.year - 1,
        profile=profile1,
        points=100,
        position=None,
    )

    Profile.objects.update_player_positions_for_year(now.year)

    assert (
        PlayerStats.objects.get(
            category="score", year=now.year, profile=profile1, points=1000
        ).position
        == 3
    )
    assert (
        PlayerStats.objects.get(
            category="score", year=now.year, profile=profile2, points=2000
        ).position
        == 2
    )
    assert (
        PlayerStats.objects.get(
            category="score", year=now.year, profile=profile3, points=3000
        ).position
        == 1
    )

    assert (
        PlayerStats.objects.get(
            category="time", year=now.year, profile=profile1, points=100
        ).position
        == 2
    )
    assert (
        PlayerStats.objects.get(
            category="time", year=now.year, profile=profile2, points=100
        ).position
        == 3
    )
    assert (
        PlayerStats.objects.get(
            category="time", year=now.year, profile=profile3, points=200
        ).position
        == 1
    )

    assert (
        PlayerStats.objects.get(category="spm_ratio", year=now.year, profile=profile1).position
        is None
    )
    assert (
        PlayerStats.objects.get(category="spm_ratio", year=now.year, profile=profile2).position
        is None
    )
    assert (
        PlayerStats.objects.get(category="spm_ratio", year=now.year, profile=profile3).position == 1
    )

    assert (
        PlayerStats.objects.get(category="spr_ratio", year=now.year, profile=profile1).position
        is None
    )
    assert (
        PlayerStats.objects.get(category="spr_ratio", year=now.year, profile=profile2).position == 2
    )
    assert (
        PlayerStats.objects.get(category="spr_ratio", year=now.year, profile=profile3).position == 1
    )

    assert (
        PlayerStats.objects.get(category="kd_ratio", year=now.year, profile=profile1).position == 2
    )
    assert (
        PlayerStats.objects.get(category="kd_ratio", year=now.year, profile=profile2).position == 1
    )
    assert (
        PlayerStats.objects.get(category="kd_ratio", year=now.year, profile=profile3).position
        is None
    )

    assert (
        PlayerStats.objects.get(
            category="weapon_hit_ratio", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        PlayerStats.objects.get(
            category="weapon_hit_ratio", year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        PlayerStats.objects.get(
            category="weapon_kill_ratio", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        PlayerStats.objects.get(
            category="weapon_kill_ratio", year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        PlayerStats.objects.get(
            category="weapon_kill_ratio", year=now.year, profile=profile3
        ).position
        == 2
    )

    # excluded
    assert (
        PlayerStats.objects.get(
            category="weapon_teamhit_ratio", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        PlayerStats.objects.get(
            category="weapon_teamhit_ratio", year=now.year, profile=profile2
        ).position
        is None
    )
    assert (
        PlayerStats.objects.get(
            category="grenade_teamhit_ratio", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        PlayerStats.objects.get(
            category="grenade_teamhit_ratio", year=now.year, profile=profile2
        ).position
        is None
    )

    assert (
        ServerStats.objects.get(
            category="score", server=server1, year=now.year, profile=profile1
        ).position
        == 1
    )
    assert (
        ServerStats.objects.get(
            category="score", server=server2, year=now.year, profile=profile1
        ).position
        == 3
    )
    assert (
        ServerStats.objects.get(
            category="score", server=server2, year=now.year, profile=profile2
        ).position
        == 2
    )
    assert (
        ServerStats.objects.get(
            category="score", server=server2, year=now.year, profile=profile3
        ).position
        == 1
    )

    assert (
        ServerStats.objects.get(
            category="kills", server=server1, year=now.year, profile=profile1
        ).position
        == 1
    )
    assert (
        ServerStats.objects.get(
            category="kills", server=server1, year=now.year, profile=profile2
        ).position
        == 2
    )
    assert (
        ServerStats.objects.get(
            category="kills", server=server1, year=now.year, profile=profile3
        ).position
        == 3
    )
    assert (
        ServerStats.objects.get(
            category="kills", server=server2, year=now.year, profile=profile3
        ).position
        == 1
    )

    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server1, year=now.year, profile=profile1
        ).position
        == 2
    )
    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server1, year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server1, year=now.year, profile=profile3
        ).position
        is None
    )
    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server2, year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server2, year=now.year, profile=profile2
        ).position
        is None
    )
    assert (
        ServerStats.objects.get(
            category="kd_ratio", server=server2, year=now.year, profile=profile3
        ).position
        == 1
    )

    assert (
        GametypeStats.objects.get(
            category="spm_ratio", gametype="VIP Escort", year=now.year, profile=profile1
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="spm_ratio", gametype="VIP Escort", year=now.year, profile=profile2
        ).position
        is None
    )

    assert (
        GametypeStats.objects.get(
            category="arrests", gametype="VIP Escort", year=now.year, profile=profile1
        ).position
        == 2
    )
    assert (
        GametypeStats.objects.get(
            category="arrests", gametype="VIP Escort", year=now.year, profile=profile3
        ).position
        == 3
    )
    assert (
        GametypeStats.objects.get(
            category="arrests", gametype="VIP Escort", year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="arrests", gametype="Rapid Deployment", year=now.year, profile=profile1
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="time", gametype="Rapid Deployment", year=now.year, profile=profile1
        ).position
        == 2
    )
    assert (
        GametypeStats.objects.get(
            category="time", gametype="Rapid Deployment", year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="score", gametype="Rapid Deployment", year=now.year, profile=profile1
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="score", gametype="Rapid Deployment", year=now.year, profile=profile2
        ).position
        == 2
    )
    assert (
        GametypeStats.objects.get(
            category="spm_ratio", gametype="Rapid Deployment", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        GametypeStats.objects.get(
            category="spm_ratio", gametype="Rapid Deployment", year=now.year, profile=profile2
        ).position
        == 1
    )
    assert (
        GametypeStats.objects.get(
            category="spr_ratio", gametype="Rapid Deployment", year=now.year, profile=profile1
        ).position
        is None
    )
    assert (
        GametypeStats.objects.get(
            category="spr_ratio", gametype="Rapid Deployment", year=now.year, profile=profile2
        ).position
        == 1
    )

    # not updated
    assert (
        PlayerStats.objects.get(
            category="score", year=now.year + 1, profile=profile1, points=10000
        ).position
        == 4
    )
    assert (
        PlayerStats.objects.get(
            category="score", year=now.year - 1, profile=profile2, points=10000
        ).position
        is None
    )
    assert (
        ServerStats.objects.get(
            category="time", year=now.year - 1, server=server2, profile=profile2
        ).position
        is None
    )
    assert MapStats.objects.get(category="time", year=now.year, profile=profile1).position is None
    assert (
        GametypeStats.objects.get(
            category="time", gametype="VIP Escort", year=now.year - 1, profile=profile1
        ).position
        is None
    )


@pytest.mark.django_db(databases=["default", "replica"])
def test_recalculate_positions(now):
    profile1, profile2, profile3 = ProfileFactory.create_batch(3)

    ps1 = PlayerStatsFactory(
        category="score", year=now.year, profile=profile1, points=3000, position=None
    )
    ps2 = PlayerStatsFactory(
        category="score", year=now.year, profile=profile2, points=1000, position=None
    )
    ps3 = PlayerStatsFactory(
        category="score", year=now.year, profile=profile3, points=2000, position=None
    )

    Profile.objects.update_player_positions_for_year(now.year)

    ps1.refresh_from_db()
    ps2.refresh_from_db()
    ps3.refresh_from_db()
    assert ps1.position == 1
    assert ps2.position == 3
    assert ps3.position == 2

    ps3.points = 3001
    ps3.save()
    Profile.objects.update_player_positions_for_year(now.year)

    ps1.refresh_from_db()
    ps2.refresh_from_db()
    ps3.refresh_from_db()
    assert ps1.position == 2
    assert ps2.position == 3
    assert ps3.position == 1

    ps3.delete()
    Profile.objects.update_player_positions_for_year(now.year)

    ps1.refresh_from_db()
    ps2.refresh_from_db()
    assert ps1.position == 1
    assert ps2.position == 2


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_positions_with_no_stats(now):
    Profile.objects.update_player_positions_for_year(now.year)  # no error
    assert PlayerStats.objects.count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_last_year_positions(now):
    profile1, profile2, profile3 = ProfileFactory.create_batch(3)

    # current year, should not be updated
    PlayerStatsFactory(
        category="score", year=now.year, profile=profile1, points=3000, position=None
    )
    PlayerStatsFactory(
        category="score", year=now.year, profile=profile2, points=1000, position=None
    )
    PlayerStatsFactory(
        category="score", year=now.year, profile=profile3, points=2000, position=None
    )

    PlayerStatsFactory(
        category="score", year=now.year - 1, profile=profile1, points=1000, position=None
    )
    PlayerStatsFactory(
        category="score", year=now.year - 1, profile=profile2, points=1001, position=None
    )

    # long before, should not be updated
    PlayerStatsFactory(
        category="score", year=now.year - 2, profile=profile1, points=1000, position=None
    )

    Profile.objects.update_player_positions_for_year(now.year - 1)

    assert (
        PlayerStats.objects.get(category="score", year=now.year, profile=profile1).position is None
    )
    assert (
        PlayerStats.objects.get(category="score", year=now.year, profile=profile2).position is None
    )
    assert (
        PlayerStats.objects.get(category="score", year=now.year, profile=profile3).position is None
    )

    assert (
        PlayerStats.objects.get(category="score", year=now.year - 1, profile=profile1).position == 2
    )
    assert (
        PlayerStats.objects.get(category="score", year=now.year - 1, profile=profile2).position == 1
    )

    assert (
        PlayerStats.objects.get(category="score", year=now.year - 2, profile=profile1).position
        is None
    )
