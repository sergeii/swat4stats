from __future__ import unicode_literals

from cacheops import invalidation
from mock import patch, PropertyMock
from django import test
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import julia

from tracker import models, signals, definitions, utils, const
from tracker.management.commands import cron_update_popular, cron_update_ranks


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()
        return super(TestCase, self).setUp()


class UpdateProfileCase(TestCase):

    def setUp(self):
        super(UpdateProfileCase, self).setUp()
        (models.ISP.objects
            .create(name='localhost', country='un')
            .ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
        )
        self.server = models.Server.objects.create(ip='127.0.0.100', port=10480, key='12345', enabled=True)

    def test_profile_field_is_not_updated_if_empty(self):
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
            server=self.server,
            gametype=definitions.MODE_BS,
            mapname=0,
            time=123,
            player_num=16,  # min players filter is in effect
            outcome=definitions.SUS_GAMES[0],
        )
        player = game.player_set.create(
            team=1,
            alias=models.Alias.objects.create(profile=profile, name='Serge', isp=None),
            ip='127.0.0.1',
            loadout=None,
        )

        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=self.server,
            game=game,
            players=[player],
        )

        cron_update_popular.Command().handle('60*60')

        p = models.Profile.objects.get(pk=profile.pk)

        self.assertEqual(p.name, 'Serge')  # updated
        self.assertEqual(p.team, 1)  # updated
        self.assertTrue(p.loadout is not None)  # older value is kept
        self.assertEqual(p.country, 'eu')  # older value is kept

    def test_vip_game(self):
        game = models.Game.objects.create(
            server=self.server,
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
        p1 = game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.match_or_create(name='Serge', ip='127.0.0.1')[0],
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

        p2 = game.player_set.create(
            team=1,
            alias=models.Alias.objects.match_or_create(name='Player', ip='127.0.0.2')[0],
            ip='127.0.0.2',

            score=77,
            kills=70,
            deaths=7,
            vip_captures=4,
            suicides=1
        )

        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=self.server,
            game=game,
            players=[p1, p2],
        )

        with patch.object(models.Profile, 'MIN_TIME', new=PropertyMock(return_value=1)), patch.object(models.Profile, 'MIN_GAMES', new=PropertyMock(return_value=1)):
            cron_update_popular.Command().handle('60*60')
            cron_update_ranks.Command().handle('60*60')

        p1 = models.Profile.objects.first()
        p2 = models.Profile.objects.last()

        self.assertEqual(models.Player.objects.count(), 2)
        self.assertEqual(models.Profile.objects.count(), 2)

        self.assertEqual(p1.name, 'Serge')
        self.assertEqual(p1.team, 0)
        self.assertIs(p1.loadout, None)
        self.assertEqual(p1.country, 'un')

        self.assertEqual(p2.name, 'Player')
        self.assertEqual(p2.team, 1)
        self.assertIs(p2.loadout, None)
        self.assertEqual(p2.country, 'un')

        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_SCORE).points,
            4400
        )
        self.assertIs(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_SCORE).position,
            None
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_GAMES).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_LOSSES).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_SPM).points,
            2200
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_SPR).points,
            4400
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_KILLS).points,
            500
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_TOP_KILLS).points,
            500
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_DEATHS).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_KDR).points,
            500
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_VIP_CAPTURES).points,
            2
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_VIP_ESCAPES).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p2, 
                category=const.STATS_SCORE).points,
            77
        )
        self.assertIs(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p2, 
                category=const.STATS_SCORE).position,
            None
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p2, 
                category=const.STATS_GAMES).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p2, 
                category=const.STATS_WINS).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p2, 
                category=const.STATS_SUICIDES).points,
            1
        )

        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, year=timezone.now().year-1)

        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p1, category=const.STATS_VIP_RESCUES)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p2, category=const.STATS_VIP_RESCUES)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p1, category=const.STATS_WINS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p2, category=const.STATS_LOSSES)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p2, category=const.STATS_KDR)

        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_SG_KILLS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_RD_BOMBS_DEFUSED)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_SG_KILLS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_COOP_HOSTAGE_ARRESTS)

    def test_coop_game(self):
        game = models.Game.objects.create(
            server=self.server,
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

        p1 = game.player_set.create(
            team=0,
            vip=True,
            admin=True,
            alias=models.Alias.objects.match_or_create(name='Serge', ip='127.0.0.1')[0],
            ip='127.0.0.1',

            time=1200,
            coop_toc_reports=10,
            coop_hostage_arrests=10,
            coop_hostage_kills=8
        )
        p2 = game.player_set.create(
            team=0,
            alias=models.Alias.objects.match_or_create(name='Player', ip='127.0.0.2')[0],
            ip='127.0.0.2',

            time=500,
            coop_hostage_arrests=12,
            coop_hostage_hits=6,
            coop_hostage_kills=7
        )

        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=self.server,
            game=game,
            players=[p1, p2],
        )

        cron_update_popular.Command().handle('60*60')
        cron_update_ranks.Command().handle('60*60')

        p1 = models.Profile.objects.first()
        p2 = models.Profile.objects.last()

        self.assertEqual(models.Player.objects.count(), 2)
        self.assertEqual(models.Profile.objects.count(), 2)


        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_COOP_TIME).points,
            1200
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_COOP_TOC_REPORTS).points,
            10
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_COOP_GAMES).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_COOP_WINS).points,
            1
        )
        self.assertEqual(
            models.Rank.objects.get(
                year=timezone.now().year, 
                profile=p1, 
                category=const.STATS_COOP_HOSTAGE_KILLS).points,
            8
        )

        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, profile=p1, category=const.STATS_COOP_LOSSES)

        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_SCORE)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_TIME)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_GAMES)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_WINS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_DRAWS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_KILLS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_DEATHS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_KILL_STREAK)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_SG_KILLS)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_VIP_KILLS_INVALID)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_VIP_ESCAPES)
        self.assertRaises(ObjectDoesNotExist, models.Rank.objects.get, category=const.STATS_RD_BOMBS_DEFUSED)


class QueryServersCommandTestCase(TestCase):

    def test_foo(self):
        pass