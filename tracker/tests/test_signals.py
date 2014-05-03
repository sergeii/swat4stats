from __future__ import unicode_literals

from cacheops import invalidation
from mock import patch
from django import test
from django.utils import timezone
import julia

from tracker import models, signals, definitions, utils, const


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()
        return super(TestCase, self).setUp()


class StreamDataSavedCase(TestCase):

    def setUp(self):
        super(StreamDataSavedCase, self).setUp()
        models.Server.objects.create(ip='127.0.0.1', port=10480, key='12345', enabled=True)
        (models.ISP.objects
            .create(name='localhost', country='un')
            .ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
        )
        self.server = models.Server.objects.first()

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
                alias=models.Alias.objects.match_or_create(name='Serge', ip='127.0.0.1')[0],
                ip='127.0.0.1'
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
        self.assertEqual(profile.game_first.pk, game.pk)
        self.assertEqual(profile.game_last.pk, game.pk)