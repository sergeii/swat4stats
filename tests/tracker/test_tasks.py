from unittest.mock import patch, PropertyMock

import pytest
from django.utils import timezone

from tracker import models, definitions, utils, tasks
from tracker.definitions import STAT


@pytest.fixture
def isp(db):
    isp = models.ISP.objects.create(name='localhost', country='un')
    isp.ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
    return isp


@pytest.fixture
def server(isp):
    return models.Server.objects.create(ip='127.0.0.100', port=10480, enabled=True)


class TestUpdatePopular:

    def test_profile_field_is_not_updated_if_empty(self, server):
        profile = models.Profile.objects.create(
            team=0,
            name='Player',
            country='eu',
            loadout=models.Loadout.objects.create(**{
                'primary': 0,
                'secondary': 0,
                'primary_ammo': 0,
                'secondary_ammo': 0,
                'head': 0,
                'body': 0,
                'equip_one': 0,
                'equip_two': 0,
                'equip_three': 0,
                'equip_four': 0,
                'equip_five': 0,
                'breacher': 0,
            })
        )
        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODE_BS,
            mapname=0,
            time=123,
            player_num=16,  # min players filter is in effect
            outcome=definitions.SUS_GAMES[0],
        )
        alias = models.Alias.objects.create(profile=profile, name='Serge', isp=None)
        game.player_set.create(
            team=1,
            alias=alias,
            ip='127.0.0.1',
            loadout=None,
        )
        profile.game_last = game
        profile.save(update_fields=['game_last'])

        tasks.update_popular(60*60)

        p = models.Profile.objects.get(pk=profile.pk)
        assert p.name == 'Serge'  # updated
        assert p.team == 1  # updated
        assert p.loadout is not None  # older value is kept
        assert p.country == 'eu'  # older value is kept


class TestUpdateRanks:

    def test_vip_game(self, server, isp):
        pro1 = models.Profile.objects.create()
        pro2 = models.Profile.objects.create()
        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODE_VIP,
            mapname=0,
            player_num=16,
            score_swat=10,
            score_sus=11,
            vict_swat=2,
            vict_sus=3,
            time=651,
            outcome=definitions.SUS_GAMES[2],
        )
        game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.create(profile=pro1, name='Serge', isp=isp),
            ip='127.0.0.1',

            score=4400,
            time=120,
            kills=500,
            deaths=1,
            teamkills=1,
            kill_streak=3,
            vip_escapes=1,
            vip_captures=2
        )
        game.player_set.create(
            team=1,
            alias=models.Alias.objects.create(profile=pro2, name='Player', isp=isp),
            ip='127.0.0.2',

            score=77,
            time=50,
            kills=70,
            deaths=7,
            vip_captures=4,
            suicides=1
        )
        pro1.game_first = game
        pro1.game_last = game
        pro1.save(update_fields=['game_first', 'game_last'])
        pro2.game_first = game
        pro2.game_last = game
        pro2.save(update_fields=['game_first', 'game_last'])

        with patch.object(models.Profile, 'MIN_TIME', new=PropertyMock(return_value=1)),\
                patch.object(models.Profile, 'MIN_GAMES', new=PropertyMock(return_value=1)):
            tasks.update_popular(60*60)
            tasks.update_ranks(60*60)

        pro1 = models.Profile.objects.get(pk=pro1.pk)
        pro2 = models.Profile.objects.get(pk=pro2.pk)

        assert pro1.name == 'Serge'
        assert pro1.team == 0
        assert pro1.loadout is None
        assert pro1.country == 'un'

        assert pro2.name == 'Player'
        assert pro2.team == 1
        assert pro2.loadout is None
        assert pro2.country == 'un'

        year = timezone.now().year

        assert models.Rank.objects.get(year=year, profile=pro1, category=STAT.SCORE).position is None
        assert models.Rank.objects.get(year=year, profile=pro2, category=STAT.SCORE).position is None

        pro1_expected_points = [
            (STAT.SCORE, 4400),
            (STAT.VIP_SCORE, 4400),
            (STAT.TIME, 120),
            (STAT.VIP_TIME, 120),
            (STAT.GAMES, 1),
            (STAT.LOSSES, 1),
            (STAT.SPM, 2200),
            (STAT.SPR, 4400),
            (STAT.KILLS, 500),
            (STAT.TOP_KILLS, 500),
            (STAT.DEATHS, 1),
            (STAT.KDR, 500),
            (STAT.VIP_CAPTURES, 2),
            (STAT.VIP_ESCAPES, 1),
        ]
        for category, points in pro1_expected_points:
            assert models.Rank.objects.get(year=year, profile=pro1, category=category).points == points

        pro1_zero_catagories = [
            STAT.VIP_RESCUES,
            STAT.BS_SCORE,
            STAT.RD_SCORE,
            STAT.SG_SCORE,
            STAT.BS_TIME,
            STAT.RD_TIME,
            STAT.RD_TIME,
            STAT.SG_TIME,
            STAT.WINS,
            STAT.SG_KILLS,
            STAT.RD_BOMBS_DEFUSED,
            STAT.COOP_HOSTAGE_ARRESTS,
        ]
        for category in pro1_zero_catagories:
            assert models.Rank.objects.filter(profile=pro1, category=category).count() == 0

        pro2_expected_points = [
            (STAT.SCORE, 77),
            (STAT.TIME, 50),
            (STAT.VIP_SCORE, 77),
            (STAT.VIP_TIME, 50),
            (STAT.GAMES, 1),
            (STAT.WINS, 1),
            (STAT.SUICIDES, 1),
        ]
        for category, points in pro2_expected_points:
            assert models.Rank.objects.get(year=year, profile=pro2, category=category).points == points

        pro2_zero_catagories = [
            STAT.VIP_RESCUES,
            STAT.LOSSES,
            STAT.KDR,
            STAT.SG_KILLS,
            STAT.RD_BOMBS_DEFUSED,
            STAT.COOP_HOSTAGE_ARRESTS,
        ]
        for category in pro2_zero_catagories:
            assert models.Rank.objects.filter(profile=pro2, category=category).count() == 0

    def test_coop_game(self, server, isp):
        pro1 = models.Profile.objects.create()
        pro2 = models.Profile.objects.create()

        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODES_COOP[0],
            mapname=0,
            player_num=5,
            time=1200,
            outcome=definitions.COMPLETED_MISSIONS[0],
        )

        models.Procedure.objects.bulk_create([
            models.Procedure(game=game, name=1, status='', score=40),
            models.Procedure(game=game, name=2, status='10', score=-10),
            models.Procedure(game=game, name=3, status='25/25', score=5),
            models.Procedure(game=game, name=4, status='14/14', score=15),
            models.Procedure(game=game, name=5, status='14/14', score=15),
            models.Procedure(game=game, name=6, status='3', score=-45),
        ])

        game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.create(profile=pro1, name='Serge', isp=isp),
            ip='127.0.0.1',

            time=1200,
            coop_toc_reports=10,
            coop_hostage_arrests=10,
            coop_hostage_kills=8
        )
        game.player_set.create(
            team=0,
            alias=models.Alias.objects.create(profile=pro2, name='Player', isp=isp),
            ip='127.0.0.2',

            time=500,
            coop_hostage_arrests=12,
            coop_hostage_hits=6,
            coop_hostage_kills=7
        )
        pro1.game_first = game
        pro1.game_last = game
        pro1.save(update_fields=['game_first', 'game_last'])
        pro2.game_first = game
        pro2.game_last = game
        pro2.save(update_fields=['game_first', 'game_last'])

        tasks.update_popular(60*60)
        tasks.update_ranks(60*60)

        pro1 = models.Profile.objects.get(pk=pro1.pk)
        pro2 = models.Profile.objects.get(pk=pro2.pk)

        year = timezone.now().year

        pro1_expected_points = [
            (STAT.COOP_TIME, 1200),
            (STAT.COOP_TOC_REPORTS, 10),
            (STAT.COOP_GAMES, 1),
            (STAT.COOP_WINS, 1),
            (STAT.COOP_HOSTAGE_KILLS, 8),
        ]
        for category, points in pro1_expected_points:
            assert models.Rank.objects.get(year=year, profile=pro1, category=category).points == points

        pro2_expected_points = [
            (STAT.COOP_TIME, 500),
            (STAT.COOP_GAMES, 1),
            (STAT.COOP_WINS, 1),
            (STAT.COOP_HOSTAGE_HITS, 6),
            (STAT.COOP_HOSTAGE_ARRESTS, 12),
            (STAT.COOP_HOSTAGE_KILLS, 7),
        ]
        for category, points in pro2_expected_points:
            assert models.Rank.objects.get(year=year, profile=pro2, category=category).points == points

        pro1_zero_catagories = [
            STAT.COOP_LOSSES,
            STAT.SCORE,
            STAT.TIME,
            STAT.GAMES,
            STAT.WINS,
            STAT.DRAWS,
            STAT.KILLS,
            STAT.DEATHS,
            STAT.KILL_STREAK,
            STAT.SG_KILLS,
            STAT.VIP_KILLS_INVALID,
            STAT.VIP_ESCAPES,
            STAT.RD_BOMBS_DEFUSED,
        ]
        for category in pro1_zero_catagories:
            assert models.Rank.objects.filter(profile=pro1, category=category).count() == 0
            assert models.Rank.objects.filter(profile=pro2, category=category).count() == 0

    def test_bs_game(self, server, isp):
        profile = models.Profile.objects.create()
        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODE_BS,
            mapname=0,
            player_num=16,
            score_swat=72,
            score_sus=73,
            vict_swat=1,
            vict_sus=0,
            time=1200,
            outcome=definitions.SWAT_GAMES[0],
        )
        game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.create(name='Serge', profile=profile, isp=isp),
            ip='127.0.0.1',

            score=63,
            time=1200,
            kills=63,
            deaths=1,
            teamkills=0,
            kill_streak=62,
        )
        profile.game_first = game
        profile.game_last = game
        profile.save(update_fields=['game_first', 'game_last'])

        tasks.update_popular(60*60)
        tasks.update_ranks(60*60)

        profile = models.Profile.objects.get(pk=profile.pk)
        year = timezone.now().year

        expected_points = [
            (STAT.SCORE, 63),
            (STAT.BS_SCORE, 63),
            (STAT.TIME, 1200),
            (STAT.BS_TIME, 1200),
            (STAT.KILL_STREAK, 62),
        ]
        for category, points in expected_points:
            assert models.Rank.objects.get(year=year, profile=profile, category=category).points == points

        zero_categories = [
            STAT.VIP_SCORE,
            STAT.COOP_SCORE,
            STAT.SG_SCORE,
            STAT.COOP_SCORE,
            STAT.VIP_TIME,
            STAT.COOP_TIME,
            STAT.SG_TIME,
            STAT.COOP_TIME,
        ]
        for category in zero_categories:
            assert models.Rank.objects.filter(profile=profile, category=category).count() == 0

    def test_sg_game(self, server, isp):
        profile = models.Profile.objects.create()
        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODE_SG,
            mapname=12,
            player_num=16,
            score_swat=0,
            score_sus=10,
            vict_swat=0,
            vict_sus=1,
            time=372,
            outcome=definitions.SUS_GAMES[4],
        )
        game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.create(name='Serge', profile=profile, isp=isp),
            ip='127.0.0.1',

            score=10,
            time=372,
            deaths=1,
        )
        profile.game_first = game
        profile.game_last = game
        profile.save(update_fields=['game_first', 'game_last'])

        tasks.update_popular(60*60)
        tasks.update_ranks(60*60)

        profile = models.Profile.objects.get(pk=profile.pk)
        year = timezone.now().year

        expected_points = [
            (STAT.SCORE, 10),
            (STAT.SG_SCORE, 10),
            (STAT.TIME, 372),
            (STAT.SG_TIME, 372),
            (STAT.DEATHS, 1),
        ]
        for category, points in expected_points:
            assert models.Rank.objects.get(year=year, profile=profile, category=category).points == points

        zero_categories = [
            STAT.BS_SCORE,
            STAT.VIP_SCORE,
            STAT.COOP_SCORE,
            STAT.COOP_SCORE,
            STAT.BS_TIME,
            STAT.VIP_TIME,
            STAT.COOP_TIME,
            STAT.COOP_TIME,
        ]
        for category in zero_categories:
            assert models.Rank.objects.filter(profile=profile, category=category).count() == 0
