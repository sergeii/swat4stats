from datetime import datetime
from functools import partial

import pytest
from pytz import UTC

from apps.tracker.models import (
    MapStats,
    PlayerStats,
    WeaponStats,
    ServerStats,
    GametypeStats,
    Profile,
)
from tests.factories.tracker import (
    PlayerFactory,
    ProfileFactory,
    MapFactory,
    WeaponFactory,
    ServerFactory,
)


@pytest.fixture
def abomb(db):
    return MapFactory(name="A-Bomb Nightclub")


@pytest.fixture
def brewer(db):
    return MapFactory(name="Brewer County Courthouse")


@pytest.fixture
def wm(db):
    return ServerFactory()


@pytest.fixture
def myt(db):
    return ServerFactory()


@pytest.fixture
def sef(db):
    return ServerFactory()


@pytest.fixture
def jogador(db, abomb, brewer, myt, wm, sef):
    jogador = ProfileFactory(
        first_seen_at=datetime(2015, 12, 4, tzinfo=UTC),
        last_seen_at=datetime(2015, 12, 31, tzinfo=UTC),
    )
    # 2014
    p1 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2014, 3, 28, tzinfo=UTC),
        game__server=wm,
        game__gametype="VIP Escort",
        game__outcome="swat_vip_escape",
        team="swat",
        kills=91,
        time=18,
        arrests=10,
        arrested=5,
        score=150,
    )
    WeaponFactory(
        player=p1, name="9mm SMG", time=10, shots=90, hits=25, kills=5, teamhits=3, teamkills=0
    )
    WeaponFactory(
        player=p1, name="Stinger", time=8, shots=8, hits=4, kills=0, teamhits=3, teamkills=0
    )

    # 2015, vip escort
    p2 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 3, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="tie",
        game__map=abomb,
        game__server=myt,
        team="swat",
        score=1400,
        time=110,
        kills=350,
        deaths=10,
        arrests=75,
        arrested=0,
        kill_streak=150,
        arrest_streak=50,
        death_streak=10,
        vip_rescues=3,
    )
    WeaponFactory(
        player=p2, name=".45 SMG", time=50, shots=89, hits=65, kills=13, teamhits=0, teamkills=0
    )
    WeaponFactory(
        player=p2, name="Shotgun", time=5, shots=1, hits=4, kills=1, teamhits=0, teamkills=0
    )
    WeaponFactory(
        player=p2, name="Stinger", time=35, shots=5, hits=3, kills=1, teamhits=2, teamkills=0
    )
    WeaponFactory(
        player=p2, name="Flashbang", time=10, shots=3, hits=0, kills=0, teamhits=3, teamkills=0
    )
    WeaponFactory(
        player=p2, name="Taser Stun Gun", time=10, shots=0, hits=0, kills=0, teamhits=0, teamkills=0
    )

    p3 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 4, 1, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_escape",
        game__map=abomb,
        game__server=myt,
        team="swat",
        time=910,
        kills=1000,
        kill_streak=1000,
        arrest_streak=30,
        deaths=0,
        arrests=30,
        arrested=25,
        score=2000,
        vip_rescues=1,
    )
    WeaponFactory(
        player=p3, name="9mm Handgun", time=800, shots=24, hits=11, kills=3, teamhits=0, teamkills=0
    )
    WeaponFactory(
        player=p3,
        name="Taser Stun Gun",
        time=110,
        shots=24,
        hits=17,
        kills=0,
        teamhits=2,
        teamkills=0,
    )
    WeaponFactory(
        player=p3, name="Shotgun", time=0, shots=0, hits=0, kills=0, teamhits=0, teamkills=0
    )

    p4 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 4, 1, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_bad_kill",
        game__map=abomb,
        game__server=wm,
        team="suspects",
        kills=0,
        deaths=0,
        time=300,
        score=0,
        arrests=0,
        arrested=5,
        vip_captures=2,
        vip_kills_invalid=1,
    )
    WeaponFactory(
        player=p4, name="Stinger", time=100, shots=3, hits=1, kills=0, teamhits=0, teamkills=0
    )
    WeaponFactory(
        player=p4, name="Nova Pump", time=75, shots=15, hits=5, kills=0, teamhits=0, teamkills=0
    )
    WeaponFactory(
        player=p4,
        name="9mm Machine Pistol",
        time=80,
        shots=90,
        hits=20,
        kills=14,
        teamhits=17,
        teamkills=0,
    )
    WeaponFactory(
        player=p4,
        name="5.56mm Light Machine Gun",
        time=50,
        shots=180,
        hits=90,
        kills=18,
        teamhits=9,
        teamkills=0,
    )
    WeaponFactory(
        player=p4, name="Shotgun", time=18, shots=5, hits=7, kills=1, teamhits=1, teamkills=1
    )

    # 2015, coop
    PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 5, 1, tzinfo=UTC),
        game__gametype="CO-OP",
        game__outcome="coop_completed",
        game__coop_score=99,
        game__time=845,
        game__map=abomb,
        game__server=sef,
        time=198,
        score=10,
        kills=1,
        deaths=1,
        arrests=5,
        coop_hostage_arrests=7,
        coop_hostage_hits=3,
        coop_hostage_incaps=2,
        coop_hostage_kills=1,
        coop_enemy_arrests=7,
        coop_enemy_incaps=3,
        coop_enemy_kills=2,
        coop_enemy_incaps_invalid=4,
        coop_enemy_kills_invalid=3,
        coop_toc_reports=28,
    )

    PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 5, 1, tzinfo=UTC),
        game__gametype="CO-OP",
        game__outcome="coop_failed",
        game__coop_score=1,
        game__time=120,
        game__map=abomb,
        game__server=sef,
        time=120,
        score=20,
        kills=2,
        deaths=1,
        arrests=2,
        coop_hostage_arrests=10,
        coop_enemy_arrests=15,
        coop_enemy_kills=5,
        coop_enemy_incaps_invalid=1,
        coop_enemy_kills_invalid=1,
        coop_toc_reports=30,
    )

    # 2015, bs, not enough players
    p5 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2015, 4, 4, tzinfo=UTC),
        game__gametype="Barricaded Suspects",
        game__outcome="tie",
        game__map=abomb,
        game__player_num=5,
        game__server=myt,
        team="swat",
        score=200,
        kills=100,
        deaths=29,
        arrests=20,
        kill_streak=18,
        arrest_streak=11,
        death_streak=6,
    )
    WeaponFactory(
        player=p5,
        name="AK-47 Machinegun",
        time=319,
        shots=192,
        hits=50,
        teamhits=0,
        kills=18,
        teamkills=7,
    )
    WeaponFactory(
        player=p5,
        name="Taser Stun Gun",
        time=120,
        shots=28,
        hits=10,
        kills=0,
        teamhits=9,
        teamkills=0,
    )
    WeaponFactory(
        player=p5, name="Shotgun", time=5, shots=1, hits=1, kills=1, teamhits=0, teamkills=0
    )

    # 2016, vip escort
    p6 = PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2016, 3, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="tie",
        game__map=brewer,
        game__server=wm,
        team="swat",
        score=1000,
        kills=350,
        deaths=10,
        arrests=10,
        kill_streak=150,
        arrest_streak=5,
        death_streak=10,
    )
    WeaponFactory(player=p6, name="AK-47 Machinegun", shots=192, hits=50, teamhits=0, kills=18)

    # 2017, bs
    PlayerFactory(
        alias__profile=jogador,
        game__date_finished=datetime(2017, 3, 22, tzinfo=UTC),
        game__gametype="Barricaded Suspects",
        game__outcome="swat_vip_escape",
        game__map=abomb,
        game__server=wm,
        team="swat",
        score=1000,
        kills=14,
        arrests=20,
        deaths=18,
        kill_streak=10,
        arrest_streak=18,
        death_streak=13,
    )

    return jogador


@pytest.fixture
def spieler(db, abomb, brewer, wm, myt, sef):
    spieler = ProfileFactory(
        first_seen_at=datetime(2013, 1, 8, tzinfo=UTC),
        last_seen_at=datetime(2016, 8, 15, tzinfo=UTC),
    )
    # 2014
    p1 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2014, 3, 24, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="sus_vip_good_kill",
        game__map=abomb,
        game__server=wm,
        team="suspects",
        kills=18,
        time=38,
        score=80,
    )
    WeaponFactory(
        player=p1, name=".45 SMG", time=30, shots=31, hits=10, kills=3, teamhits=9, teamkills=2
    )
    WeaponFactory(
        player=p1, name="Flashbang", time=8, shots=8, hits=3, kills=0, teamhits=3, teamkills=0
    )

    # 2015, vip escort
    p2 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2015, 9, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_escape",
        game__map=abomb,
        game__server=myt,
        team="swat",
        vip=True,
        kills=5,
        deaths=0,
        kill_streak=5,
        arrest_streak=0,
        death_streak=0,
    )
    WeaponFactory(
        player=p2, name="9mm SMG", time=180, shots=30, hits=20, kills=2, teamhits=0, teamkills=0
    )

    # 2015, coop
    PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2015, 11, 30, tzinfo=UTC),
        game__gametype="CO-OP",
        game__outcome="coop_failed",
        game__coop_score=0,
        game__map=abomb,
        game__server=sef,
        time=600,
        score=5,
        kills=5,
        deaths=1,
    )

    # 2015, rd
    p3 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2015, 1, 18, tzinfo=UTC),
        game__gametype="Rapid Deployment",
        game__outcome="swat_rd",
        game__map=brewer,
        game__server=myt,
        team="suspects",
        kills=7,
        arrests=1,
        arrested=8,
        time=901,
        score=10,
    )
    WeaponFactory(
        player=p3, name="9mm SMG", time=900, shots=7, hits=2, kills=1, teamhits=0, teamkills=0
    )

    # 2016, vip escort
    p4 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2016, 5, 13, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_escape",
        game__map=abomb,
        game__server=wm,
        team="swat",
        vip=True,
        kills=1,
        score=11,
        time=189,
        deaths=0,
        arrests=0,
        arrested=8,
        vip_escapes=1,
        kill_streak=1,
        arrest_streak=0,
        death_streak=0,
    )
    WeaponFactory(
        player=p4, name="9mm SMG", time=80, shots=100, hits=75, kills=8, teamhits=7, teamkills=0
    )
    WeaponFactory(
        player=p4,
        name="Suppressed 9mm SMG",
        time=80,
        shots=55,
        hits=25,
        kills=5,
        teamhits=0,
        teamkills=0,
    )
    WeaponFactory(
        player=p4,
        name="Less Lethal Shotgun",
        time=29,
        shots=8,
        hits=1,
        kills=0,
        teamhits=5,
        teamkills=0,
    )
    WeaponFactory(
        player=p4, name="Taser Stun Gun", time=10, shots=0, hits=0, kills=0, teamhits=0, teamkills=0
    )

    p5 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2016, 5, 13, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_bad_kill",
        game__map=brewer,
        game__server=wm,
        team="swat",
        vip=True,
        score=18,
        kills=18,
        time=90,
        deaths=1,
        arrests=0,
        arrested=10,
        kill_streak=18,
        arrest_streak=0,
        death_streak=1,
    )
    WeaponFactory(
        player=p5,
        name="Taser Stun Gun",
        time=90,
        shots=12,
        hits=12,
        kills=0,
        teamhits=0,
        teamkills=0,
    )
    WeaponFactory(
        player=p5,
        name="Suppressed 9mm SMG",
        time=15,
        shots=5,
        hits=1,
        kills=0,
        teamhits=0,
        teamkills=0,
    )

    # 2016, vip, not enough players
    p6 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2016, 6, 1, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="tie",
        game__map=brewer,
        game__server=wm,
        game__player_num=9,
        team="suspects",
        score=68,
        kills=11,
        time=900,
        deaths=8,
        arrests=10,
        arrested=3,
        kill_streak=7,
        arrest_streak=4,
        death_streak=3,
    )
    WeaponFactory(
        player=p6, name="9mm SMG", time=500, shots=120, hits=90, kills=5, teamhits=3, teamkills=0
    )
    WeaponFactory(
        player=p6,
        name="Suppressed 9mm SMG",
        time=200,
        shots=55,
        hits=25,
        kills=6,
        teamhits=5,
        teamkills=1,
    )
    WeaponFactory(
        player=p6,
        name="Taser Stun Gun",
        time=100,
        shots=20,
        hits=12,
        kills=0,
        teamhits=1,
        teamkills=0,
    )

    # 2016, coop
    PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2016, 5, 28, tzinfo=UTC),
        game__gametype="CO-OP",
        game__outcome="coop_failed",
        game__coop_score=0,
        game__time=120,
        game__map=abomb,
        game__server=sef,
        time=300,
        score=5,
        kills=5,
        deaths=1,
        arrests=1,
        kill_streak=5,
        arrest_streak=0,
        death_streak=1,
        coop_hostage_hits=12,
        coop_hostage_incaps=3,
        coop_hostage_kills=7,
        coop_enemy_kills=1,
        coop_enemy_incaps_invalid=2,
        coop_enemy_kills_invalid=5,
        coop_toc_reports=12,
    )

    # 2016, rd
    p7 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2016, 12, 31, tzinfo=UTC),
        game__gametype="Rapid Deployment",
        game__outcome="sus_rd",
        game__map=abomb,
        game__server=myt,
        team="swat",
        kills=17,
        arrests=1,
        arrested=1,
        deaths=8,
        time=300,
        rd_bombs_defused=1,
        score=27,
        kill_streak=8,
        arrest_streak=1,
        death_streak=7,
    )
    WeaponFactory(
        player=p7, name="9mm SMG", time=100, shots=100, hits=75, kills=17, teamhits=3, teamkills=5
    )
    WeaponFactory(
        player=p7,
        name="Less Lethal Shotgun",
        time=200,
        shots=18,
        hits=17,
        kills=0,
        teamhits=1,
        teamkills=0,
    )
    WeaponFactory(
        player=p7,
        name="Cobra Stun Gun",
        time=100,
        shots=9,
        hits=6,
        kills=0,
        teamhits=3,
        teamkills=0,
    )
    WeaponFactory(
        player=p7, name="Taser Stun Gun", time=25, shots=5, hits=1, kills=0, teamhits=0, teamkills=0
    )

    # 2017
    p8 = PlayerFactory(
        alias__profile=spieler,
        game__date_finished=datetime(2017, 1, 2, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__outcome="swat_vip_escape",
        game__map=brewer,
        game__server=myt,
        team="swat",
        vip=True,
        kills=10,
        deaths=0,
        kill_streak=10,
        arrest_streak=0,
        death_streak=0,
    )
    WeaponFactory(
        player=p8,
        name="Suppressed 9mm SMG",
        time=100,
        shots=23,
        hits=11,
        kills=3,
        teamhits=1,
        teamkills=0,
    )
    WeaponFactory(
        player=p8,
        name="Less Lethal Shotgun",
        time=70,
        shots=45,
        hits=17,
        kills=0,
        teamhits=9,
        teamkills=0,
    )
    WeaponFactory(
        player=p8, name="Cobra Stun Gun", time=30, shots=2, hits=1, kills=0, teamhits=0, teamkills=0
    )

    return spieler


def flatten_stats(stat_items, *keys):
    result = {}
    for item in stat_items:
        nested_item = result
        for key in keys:
            nested_key = item.pop(key)
            nested_item = nested_item.setdefault(nested_key, {})
        nested_item.update(item)
    return result


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_player_stats(db, spieler, jogador):
    Profile.objects.update_stats_for_profile(jogador)
    Profile.objects.update_stats_for_profile(spieler)

    jogador_stats = partial(PlayerStats.objects.get, year=2015, profile=jogador)
    assert jogador_stats(category="draws").points == 1
    assert jogador_stats(category="wins").points == 1
    assert jogador_stats(category="losses").points == 1
    assert jogador_stats(category="games").points == 3
    assert jogador_stats(category="score").points == 3400
    assert jogador_stats(category="time").points == 1320
    assert jogador_stats(category="top_score").points == 2000
    assert jogador_stats(category="kills").points == 1350
    assert jogador_stats(category="arrests").points == 105
    assert jogador_stats(category="arrested").points == 30
    assert jogador_stats(category="deaths").points == 10
    assert jogador_stats(category="top_death_streak").points == 10
    assert jogador_stats(category="top_kill_streak").points == 1000
    assert jogador_stats(category="top_arrest_streak").points == 50
    assert jogador_stats(category="spm_ratio").points == 154.5455
    assert jogador_stats(category="spr_ratio").points == 1133.3333
    assert jogador_stats(category="kd_ratio").points == 135
    assert jogador_stats(category="grenade_shots").points == 11
    assert jogador_stats(category="grenade_hits").points == 4
    assert jogador_stats(category="grenade_kills").points == 1
    assert jogador_stats(category="grenade_teamhits").points == 5
    assert jogador_stats(category="grenade_hit_ratio").points == 0.3636
    assert jogador_stats(category="weapon_shots").points == 404
    assert jogador_stats(category="weapon_hits").points == 202
    assert jogador_stats(category="weapon_kills").points == 50
    assert jogador_stats(category="weapon_teamhits").points == 27
    assert jogador_stats(category="weapon_kill_ratio").points == 0.1238
    assert jogador_stats(category="weapon_hit_ratio").points == 0.5
    assert jogador_stats(category="weapon_teamhit_ratio").points == 0.0668

    spieler_stats = partial(PlayerStats.objects.get, year=2016, profile=spieler)
    assert spieler_stats(category="wins").points == 2
    assert spieler_stats(category="losses").points == 1
    assert spieler_stats(category="games").points == 3
    assert spieler_stats(category="score").points == 56
    assert spieler_stats(category="time").points == 579
    assert spieler_stats(category="top_score").points == 27
    assert spieler_stats(category="kills").points == 36
    assert spieler_stats(category="deaths").points == 9
    assert spieler_stats(category="arrests").points == 1
    assert spieler_stats(category="arrested").points == 19
    assert spieler_stats(category="kd_ratio").points == 4
    assert spieler_stats(category="spm_ratio").points == 5.8031
    assert spieler_stats(category="spr_ratio").points == 18.6667
    assert spieler_stats(category="top_death_streak").points == 7
    assert spieler_stats(category="top_kill_streak").points == 18
    assert spieler_stats(category="top_arrest_streak").points == 1
    assert spieler_stats(category="weapon_shots").points == 260
    assert spieler_stats(category="weapon_hits").points == 176
    assert spieler_stats(category="weapon_kills").points == 30
    assert spieler_stats(category="weapon_teamhits").points == 10
    assert spieler_stats(category="weapon_hit_ratio").points == 0.6769
    assert spieler_stats(category="weapon_teamhit_ratio").points == 0.0385

    assert (
        PlayerStats.objects.filter(
            year=2016, profile=spieler, category__in=["draws", "grenade_hits", "grenade_shots"]
        ).count()
        == 0
    )

    assert PlayerStats.objects.filter(year__in=[2014, 2016], profile=jogador).count() == 0
    assert PlayerStats.objects.filter(year__in=[2014, 2015], profile=spieler).count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_player_stats_for_empty_profile(db):
    profile1 = ProfileFactory(
        first_seen_at=datetime(2015, 12, 4, tzinfo=UTC),
        last_seen_at=datetime(2015, 12, 31, tzinfo=UTC),
    )
    profile2 = ProfileFactory(first_seen_at=None, last_seen_at=None)

    Profile.objects.update_stats_for_profile(profile1)
    Profile.objects.update_stats_for_profile(profile2)

    assert PlayerStats.objects.count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_weapon_stats(db, jogador, spieler):
    Profile.objects.update_stats_for_profile(jogador)
    Profile.objects.update_stats_for_profile(spieler)

    jogador_stats_qs = (
        WeaponStats.objects.filter(profile=jogador)
        .order_by("year", "category", "weapon")
        .values("year", "weapon", "category", "points")
    )
    jogador_stats = flatten_stats(jogador_stats_qs, "year", "weapon", "category")

    assert jogador_stats[2015] == {
        ".45 SMG": {
            "hits": {"points": 65.0},
            "kills": {"points": 13.0},
            "shots": {"points": 89.0},
            "time": {"points": 50.0},
            "hit_ratio": {"points": 0.7303},
            "kill_ratio": {"points": 0.1461},
        },
        "Shotgun": {
            "hits": {"points": 11.0},
            "teamhits": {"points": 1.0},
            "teamkills": {"points": 1.0},
            "kills": {"points": 2.0},
            "shots": {"points": 6.0},
            "time": {"points": 23.0},
            "hit_ratio": {"points": 1.8333},
            "teamhit_ratio": {"points": 0.1667},
            "kill_ratio": {"points": 0.3333},
        },
        "Stinger": {
            "hits": {"points": 4.0},
            "teamhits": {"points": 2.0},
            "kills": {"points": 1.0},
            "shots": {"points": 8.0},
            "time": {"points": 135.0},
            "hit_ratio": {"points": 0.5},
            "teamhit_ratio": {"points": 0.25},
            "kill_ratio": {"points": 0.125},
        },
        "Flashbang": {
            "teamhits": {"points": 3.0},
            "shots": {"points": 3.0},
            "time": {"points": 10.0},
            "teamhit_ratio": {"points": 1.0},
        },
        "9mm Handgun": {
            "hits": {"points": 11.0},
            "kills": {"points": 3.0},
            "shots": {"points": 24.0},
            "time": {"points": 800.0},
            "hit_ratio": {"points": 0.4583},
            "kill_ratio": {"points": 0.125},
        },
        "Taser Stun Gun": {
            "hits": {"points": 17.0},
            "teamhits": {"points": 2.0},
            "shots": {"points": 24.0},
            "time": {"points": 120.0},
            "hit_ratio": {"points": 0.7083},
            "teamhit_ratio": {"points": 0.0833},
        },
        "Nova Pump": {
            "hits": {"points": 5.0},
            "shots": {"points": 15.0},
            "time": {"points": 75.0},
            "hit_ratio": {"points": 0.3333},
        },
        "9mm Machine Pistol": {
            "hits": {"points": 20.0},
            "teamhits": {"points": 17.0},
            "kills": {"points": 14.0},
            "shots": {"points": 90.0},
            "time": {"points": 80.0},
            "hit_ratio": {"points": 0.2222},
            "kill_ratio": {"points": 0.1556},
            "teamhit_ratio": {"points": 0.1889},
        },
        "5.56mm Light Machine Gun": {
            "hits": {"points": 90.0},
            "teamhits": {"points": 9.0},
            "kills": {"points": 18.0},
            "shots": {"points": 180.0},
            "time": {"points": 50.0},
            "hit_ratio": {"points": 0.5},
            "kill_ratio": {"points": 0.1},
            "teamhit_ratio": {"points": 0.05},
        },
    }

    spieler_stats_qs = (
        WeaponStats.objects.filter(profile=spieler)
        .order_by("year", "category", "weapon")
        .values("year", "weapon", "category", "points")
    )
    spieler_stats = flatten_stats(spieler_stats_qs, "year", "weapon", "category")

    assert spieler_stats[2016] == {
        "Suppressed 9mm SMG": {
            "hits": {"points": 26.0},
            "kills": {"points": 5.0},
            "shots": {"points": 60.0},
            "time": {"points": 95.0},
            "hit_ratio": {"points": 0.4333},
            "kill_ratio": {"points": 0.0833},
        },
        "9mm SMG": {
            "hits": {"points": 150.0},
            "teamhits": {"points": 10.0},
            "kills": {"points": 25.0},
            "teamkills": {"points": 5.0},
            "shots": {"points": 200.0},
            "time": {"points": 180.0},
            "hit_ratio": {"points": 0.75},
            "kill_ratio": {"points": 0.125},
            "teamhit_ratio": {"points": 0.05},
        },
        "Taser Stun Gun": {
            "hits": {"points": 13.0},
            "shots": {"points": 17.0},
            "time": {"points": 125.0},
            "hit_ratio": {"points": 0.7647},
        },
        "Less Lethal Shotgun": {
            "hits": {"points": 18.0},
            "teamhits": {"points": 6.0},
            "shots": {"points": 26.0},
            "time": {"points": 229.0},
            "hit_ratio": {"points": 0.6923},
            "teamhit_ratio": {"points": 0.2308},
        },
        "Cobra Stun Gun": {
            "hits": {"points": 6.0},
            "teamhits": {"points": 3.0},
            "shots": {"points": 9.0},
            "time": {"points": 100.0},
            "hit_ratio": {"points": 0.6667},
            "teamhit_ratio": {"points": 0.3333},
        },
    }

    assert WeaponStats.objects.filter(year__in=[2014, 2016], profile=jogador).count() == 0
    assert WeaponStats.objects.filter(year__in=[2014, 2015], profile=spieler).count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_server_stats(db, spieler, jogador, myt, wm, sef):
    Profile.objects.update_stats_for_profile(jogador)
    Profile.objects.update_stats_for_profile(spieler)

    jogador_stats_qs = (
        ServerStats.objects.filter(profile=jogador)
        .order_by("year", "category", "server_id")
        .values("year", "server_id", "category", "points")
    )
    jogador_stats = flatten_stats(jogador_stats_qs, "year", "server_id", "category")

    assert jogador_stats[2015] == {
        myt.pk: {
            "score": {"points": 3400.0},
            "time": {"points": 1020.0},
            "games": {"points": 2.0},
            "kills": {"points": 1350.0},
            "deaths": {"points": 10.0},
            "arrests": {"points": 105.0},
            "kd_ratio": {"points": 135.0},
            "spr_ratio": {"points": 1700.0},
            "spm_ratio": {"points": 200.0},
            "top_kill_streak": {"points": 1000.0},
            "top_arrest_streak": {"points": 50.0},
        },
        wm.pk: {
            "time": {"points": 300.0},
            "games": {"points": 1.0},
        },
        sef.pk: {
            "coop_score": {"points": 100.0},
            "coop_games": {"points": 2.0},
            "coop_time": {"points": 965.0},
        },
    }

    spieler_stats_qs = (
        ServerStats.objects.filter(profile=spieler)
        .order_by("year", "category", "server_id")
        .values("year", "server_id", "category", "points")
    )
    spieler_stats = flatten_stats(spieler_stats_qs, "year", "server_id", "category")

    assert spieler_stats[2016] == {
        myt.pk: {
            "score": {"points": 27.0},
            "time": {"points": 300.0},
            "games": {"points": 1.0},
            "kills": {"points": 17.0},
            "deaths": {"points": 8.0},
            "arrests": {"points": 1.0},
            "kd_ratio": {"points": 2.125},
            "spm_ratio": {"points": 5.4},
            "spr_ratio": {"points": 27.0},
            "top_kill_streak": {"points": 8.0},
            "top_arrest_streak": {"points": 1.0},
        },
        wm.pk: {
            "score": {"points": 29.0},
            "time": {"points": 279.0},
            "games": {"points": 2.0},
            "kills": {"points": 19.0},
            "deaths": {"points": 1.0},
            "kd_ratio": {"points": 19.0},
            "spm_ratio": {"points": 6.2366},
            "spr_ratio": {"points": 14.5},
            "top_kill_streak": {"points": 18.0},
        },
        sef.pk: {
            "coop_games": {"points": 1.0},
            "coop_time": {"points": 120.0},
        },
    }

    assert ServerStats.objects.filter(year__in=[2014, 2016], profile=jogador).count() == 0
    assert ServerStats.objects.filter(year__in=[2014, 2015], profile=spieler).count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_map_stats(abomb, brewer, spieler, jogador):
    profile = ProfileFactory(
        first_seen_at=datetime(2015, 12, 4, tzinfo=UTC),
        last_seen_at=datetime(2015, 12, 31, tzinfo=UTC),
    )

    # past year
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2014, 3, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="swat_vip_escape",
        team="swat",
        score=150,
        time=900,
        kills=29,
        deaths=10,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2014, 3, 29, tzinfo=UTC),
        game__gametype="CO-OP",
        game__map=abomb,
        game__outcome="coop_completed",
        game__time=300,
        game__coop_score=99,
        time=1000,  # irrelevant in CO-OP
        score=150,
    )  # also irrelevant in CO-OP
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2014, 6, 1, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=brewer,
        game__outcome="swat_vip_bad_kill",
        team="swat",
        time=901,
        score=175,
    )

    # current year
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 3, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="tie",
        team="swat",
        time=300,
        score=45,
        kills=20,
        kill_streak=11,
        deaths=8,
        arrests=2,
        arrest_streak=1,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 3, 29, tzinfo=UTC),
        game__gametype="CO-OP",
        game__map=abomb,
        game__outcome="coop_failed",
        game__time=30,  # mission failed so this doesnt count
        game__coop_score=10,
        time=90,
        kills=10,
        kill_streak=9,
        deaths=1,
        arrests=5,
        arrest_streak=4,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 4, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="swat_vip_escape",
        team="suspects",
        time=100,
        score=50,
        kills=39,
        kill_streak=25,
        deaths=3,
        arrests=3,
        arrest_streak=1,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 27, tzinfo=UTC),
        game__gametype="CO-OP",
        game__map=abomb,
        game__outcome="coop_completed",
        game__time=200,
        game__coop_score=75,
        time=1800,
        kills=1,
        kill_streak=1,
        arrests=3,
        arrest_streak=3,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 28, tzinfo=UTC),
        game__player_num=4,  # too few players
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="swat_vip_escape",
        team="swat",
        time=900,
        deaths=1,
        kills=1,
        kill_streak=1,
        arrests=2,
        arrest_streak=2,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 28, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="swat_vip_escape",
        team="swat",
        time=61,
        score=10,
        deaths=4,
        kills=0,
        kill_streak=0,
        arrests=1,
        arrest_streak=1,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 30, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=abomb,
        game__outcome="swat_vip_bad_kill",
        team="suspects",
        time=81,
        score=20,
        deaths=2,
        kills=1,
        kill_streak=1,
        arrests=0,
        arrest_streak=0,
    )
    PlayerFactory(
        alias__profile=profile,
        game__date_finished=datetime(2015, 12, 31, tzinfo=UTC),
        game__gametype="VIP Escort",
        game__map=brewer,
        game__outcome="tie",
        score=30,
        kills=10,
        kill_streak=10,
        vip=True,
        deaths=1,
        time=181,
        team="swat",
        arrests=0,
        arrest_streak=0,
    )

    Profile.objects.update_stats_for_profile(profile)
    Profile.objects.update_stats_for_profile(spieler)

    map_stats = (
        MapStats.objects.filter(profile=profile)
        .order_by("year", "category", "map_id")
        .values("year", "map_id", "category", "points")
    )
    stats = flatten_stats(map_stats, "year", "map_id", "category")

    assert stats[2015] == {
        abomb.pk: {
            "games": {"points": 4.0},
            "time": {"points": 542.0},
            "kills": {"points": 60.0},
            "arrests": {"points": 6.0},
            "deaths": {"points": 17.0},
            "score": {"points": 125.0},
            "wins": {"points": 1.0},
            "losses": {"points": 2.0},
            "draws": {"points": 1.0},
            "kd_ratio": {"points": 3.5294},
            "spm_ratio": {"points": 13.8376},
            "spr_ratio": {"points": 31.25},
            "top_score": {"points": 50.0},
            "top_kill_streak": {"points": 25.0},
            "top_arrest_streak": {"points": 1.0},
            "coop_time": {"points": 230.0},
            "coop_best_time": {"points": 200.0},
            "coop_worst_time": {"points": 200.0},
            "coop_score": {"points": 85.0},
            "coop_top_score": {"points": 75.0},
            "coop_games": {"points": 2.0},
            "coop_wins": {"points": 1.0},
            "coop_losses": {"points": 1.0},
        },
        brewer.pk: {
            "games": {"points": 1.0},
            "time": {"points": 181.0},
            "kills": {"points": 10.0},
            "deaths": {"points": 1.0},
            "score": {"points": 30.0},
            "draws": {"points": 1.0},
            "kd_ratio": {"points": 10.0},
            "spm_ratio": {"points": 9.9448},
            "spr_ratio": {"points": 30},
            "top_score": {"points": 30.0},
            "top_kill_streak": {"points": 10.0},
        },
    }

    # no exception
    Profile.objects.update_stats_for_profile(ProfileFactory())


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_gametype_stats(db, spieler, jogador):
    Profile.objects.update_stats_for_profile(jogador)
    Profile.objects.update_stats_for_profile(spieler)

    jogador_stats_qs = (
        GametypeStats.objects.filter(profile=jogador)
        .order_by("year", "category", "gametype")
        .values("year", "gametype", "category", "points")
    )
    jogador_stats = flatten_stats(jogador_stats_qs, "year", "gametype", "category")

    assert jogador_stats[2015] == {
        "VIP Escort": {
            "score": {"points": 3400.0},
            "top_score": {"points": 2000.0},
            "time": {"points": 1320.0},
            "kills": {"points": 1350.0},
            "arrests": {"points": 105.0},
            "top_arrest_streak": {"points": 50.0},
            "top_kill_streak": {"points": 1000.0},
            "games": {"points": 3.0},
            "wins": {"points": 1.0},
            "losses": {"points": 1.0},
            "draws": {"points": 1.0},
            "spm_ratio": {"points": 154.5455},
            "spr_ratio": {"points": 1133.3333},
            "vip_captures": {"points": 2.0},
            "vip_rescues": {"points": 4.0},
            "vip_kills_invalid": {"points": 1.0},
        },
        "CO-OP": {
            "coop_score": {"points": 100.0},
            "coop_top_score": {"points": 99.0},
            "coop_time": {"points": 965.0},
            "coop_games": {"points": 2.0},
            "coop_wins": {"points": 1.0},
            "coop_losses": {"points": 1.0},
            "coop_hostage_arrests": {"points": 17.0},
            "coop_hostage_hits": {"points": 3.0},
            "coop_hostage_incaps": {"points": 2.0},
            "coop_hostage_kills": {"points": 1.0},
            "coop_enemy_arrests": {"points": 22.0},
            "coop_enemy_incaps": {"points": 3.0},
            "coop_enemy_kills": {"points": 7.0},
            "coop_enemy_incaps_invalid": {"points": 5.0},
            "coop_enemy_kills_invalid": {"points": 4.0},
            "coop_toc_reports": {"points": 58.0},
        },
    }

    spieler_stats_qs = (
        GametypeStats.objects.filter(profile=spieler)
        .order_by("year", "category", "gametype")
        .values("year", "gametype", "category", "points")
    )
    spieler_stats = flatten_stats(spieler_stats_qs, "year", "gametype", "category")

    assert spieler_stats[2016] == {
        "VIP Escort": {
            "score": {"points": 29.0},
            "top_score": {"points": 18.0},
            "time": {"points": 279.0},
            "kills": {"points": 19.0},
            "top_kill_streak": {"points": 18.0},
            "games": {"points": 2.0},
            "wins": {"points": 2.0},
            "spm_ratio": {"points": 6.2366},
            "spr_ratio": {"points": 14.5},
            "vip_escapes": {"points": 1.0},
            "vip_times": {"points": 2.0},
            "vip_wins": {"points": 2.0},
        },
        "CO-OP": {
            "coop_time": {"points": 120.0},
            "coop_games": {"points": 1.0},
            "coop_losses": {"points": 1.0},
            "coop_hostage_hits": {"points": 12.0},
            "coop_hostage_incaps": {"points": 3.0},
            "coop_hostage_kills": {"points": 7.0},
            "coop_enemy_kills": {"points": 1.0},
            "coop_enemy_incaps_invalid": {"points": 2.0},
            "coop_enemy_kills_invalid": {"points": 5.0},
            "coop_toc_reports": {"points": 12.0},
        },
        "Rapid Deployment": {
            "score": {"points": 27.0},
            "top_score": {"points": 27.0},
            "time": {"points": 300.0},
            "kills": {"points": 17.0},
            "arrests": {"points": 1.0},
            "top_kill_streak": {"points": 8.0},
            "top_arrest_streak": {"points": 1.0},
            "games": {"points": 1.0},
            "losses": {"points": 1.0},
            "spm_ratio": {"points": 5.4},
            "spr_ratio": {"points": 27.0},
            "rd_bombs_defused": {"points": 1.0},
        },
    }
