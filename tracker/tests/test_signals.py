from __future__ import unicode_literals

from cacheops import invalidation
from mock import patch
from django import test
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import julia

from tracker import models, signals, definitions, utils, const


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()
        return super(TestCase, self).setUp()


class StreamDataReceivedCase(TestCase):

    def setUp(self):
        super(StreamDataReceivedCase, self).setUp()
        models.Server.objects.create(ip='127.0.0.1', port=10480, key='12345', enabled=True)
        (models.ISP.objects
            .create(name='localhost', country='un')
            .ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
        )
        self.server = models.Server.objects.first()

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
            **models.Player.profile_alias(name='Serge', ip='127.0.0.1')
        )
        models.Score.objects.bulk_create([
            models.Score(player=p1, category=const.STATS_SCORE, points=4400),
            models.Score(player=p1, category=const.STATS_TIME, points=120),
            models.Score(player=p1, category=const.STATS_KILLS, points=500),
            models.Score(player=p1, category=const.STATS_DEATHS, points=1),
            models.Score(player=p1, category=const.STATS_TEAMKILLS, points=1),
            models.Score(player=p1, category=const.STATS_KILL_STREAK, points=3),
            models.Score(player=p1, category=const.STATS_VIP_ESCAPES, points=1),
            models.Score(player=p1, category=const.STATS_VIP_CAPTURES, points=4),
            models.Score(player=p1, category=const.STATS_COOP_HOSTAGE_ARRESTS, points=10),
            models.Score(player=p1, category=const.STATS_COOP_HOSTAGE_KILLS, points=8),
        ])

        p2 = game.player_set.create(
            team=1,
            **models.Player.profile_alias(name='Player', ip='127.0.0.2')
        )
        models.Score.objects.bulk_create([
            models.Score(player=p2, category=const.STATS_SCORE, points=77),
            models.Score(player=p2, category=const.STATS_KILLS, points=70),
            models.Score(player=p2, category=const.STATS_DEATHS, points=7),
            models.Score(player=p2, category=const.STATS_VIP_CAPTURES, points=4),
            models.Score(player=p2, category=const.STATS_SG_KILLS, points=1),
            models.Score(player=p2, category=const.STATS_RD_BOMBS_DEFUSED, points=3),
            models.Score(player=p2, category=const.STATS_SG_KILLS, points=3),
        ])

        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=self.server,
            game=game,
            players=[p1, p2],
        )

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
            4
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
            **models.Player.profile_alias(name='Serge', ip='127.0.0.1')
        )
        p2 = game.player_set.create(
            team=0,
            **models.Player.profile_alias(name='Player', ip='127.0.0.2')
        )

        models.Score.objects.bulk_create([
            models.Score(player=p1, category=const.STATS_TIME, points=1200),
            models.Score(player=p1, category=const.STATS_COOP_TOC_REPORTS, points=10),
            models.Score(player=p1, category=const.STATS_COOP_HOSTAGE_ARRESTS, points=10),
            models.Score(player=p1, category=const.STATS_COOP_HOSTAGE_KILLS, points=8),

            models.Score(player=p1, category=const.STATS_SCORE, points=100),
            models.Score(player=p1, category=const.STATS_KILLS, points=2),
        ])
        models.Score.objects.bulk_create([
            models.Score(player=p2, category=const.STATS_TIME, points=500),
            models.Score(player=p2, category=const.STATS_COOP_HOSTAGE_ARRESTS, points=12),
            models.Score(player=p2, category=const.STATS_COOP_HOSTAGE_HITS, points=6),
            models.Score(player=p2, category=const.STATS_COOP_HOSTAGE_KILLS, points=4),

            models.Score(player=p2, category=const.STATS_SCORE, points=100),
            models.Score(player=p2, category=const.STATS_VIP_CAPTURES, points=4),
            models.Score(player=p2, category=const.STATS_SG_KILLS, points=1),
            models.Score(player=p2, category=const.STATS_RD_BOMBS_DEFUSED, points=3),
            models.Score(player=p2, category=const.STATS_SG_KILLS, points=3),
        ])

        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=self.server,
            game=game,
            players=[p1, p2],
        )

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

    def test_last_seen_is_updated(self):
        now_cached = timezone.now().replace(microsecond=0)
        with patch.object(timezone, 'now') as mock:
            mock.return_value = now_cached
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
                **models.Player.profile_alias(name='Serge', ip='127.0.0.1')
            )

            signals.stream_data_saved.send(
                sender=None,
                data=julia.node.DictValueNode(raw={}, pattern={}),
                server=self.server,
                game=game,
                players=[p1,],
            )

        profile = models.Profile.objects.get()
        self.assertEqual(profile.last_seen, now_cached)
        self.assertEqual(profile.last_seen, profile.date_played)