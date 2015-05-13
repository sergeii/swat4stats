from __future__ import unicode_literals

from django import test
from django.utils import timezone
from cacheops import invalidation
from mock import patch
import julia

from tracker import models, signals, definitions, utils


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()
        return super(TestCase, self).setUp()


class StreamDataSavedCase(TestCase):

    def setUp(self):
        super(StreamDataSavedCase, self).setUp()
        (models.ISP.objects
            .create(name='localhost', country='un')
            .ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
        )
        models.Server.objects.create(ip='127.0.0.1', port=10480, enabled=True)
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

    def test_server_is_relisted_when_data_is_saved(self):
        server = models.Server.objects.create(ip='127.0.0.1', port=10450, listed=False)
        game = models.Game.objects.create(
            server=server,
            gametype=definitions.MODE_VIP,
            mapname=0,
            player_num=16,
            time=651,
            outcome=definitions.SUS_GAMES[2],
        )
        signals.stream_data_saved.send(
            sender=None,
            data=julia.node.DictValueNode(raw={}, pattern={}),
            server=server,
            game=game,
            players=[],
        )

        self.assertTrue(models.Server.objects.get(pk=server.pk).listed)


class UpdateServerCountryTestCase(test.TestCase):

    def setUp(self):
        (models.ISP.objects.create(name='foo', country='zz')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(),
                range_to=utils.force_ipy('127.0.0.255').int()
            )
        )

    def test_country_is_updated_for_new_instances(self):
        server = models.Server.objects.create_server('127.0.0.1', 10480)
        self.assertEqual(models.Server.objects.get(pk=server.pk).country, 'zz')

    def test_country_is_updated_if_ip_changed(self):
        server = models.Server.objects.create_server('127.0.0.1', 10480, country='aa')
        server.ip = '127.0.0.2'
        server.save()
        self.assertEqual(models.Server.objects.get(pk=server.pk).country, 'zz')

    def test_country_is_updated_if_country_is_empty(self):
        server = models.Server.objects.create_server('127.0.0.1', 10480, country='aa')
        server.country = None
        server.save()
        self.assertEqual(models.Server.objects.get(pk=server.pk).country, 'zz')
