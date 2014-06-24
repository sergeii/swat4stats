from __future__ import unicode_literals

import datetime

from django import test
from cacheops import invalidation
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import force_text

from mock import patch

from tracker import views, models, utils


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()
        cache.clear()
        return super(TestCase, self).setUp()


class WhoisApiTestCase(TestCase):
    valid_qs = (
        '0=foo&1=whois&2=ham&3=Serge%09127.0.0.1',
        '0=spam&1=whois&2=ham&3=Serge2%09127.0.0.1',
    )
    invalid_qs = (
        '',  # empty qs
        '0=foo',  # only hash is present
        '0=foo&1=whois',
        '0=foo&1=whois&3=baz',
        '0=foo&1=invalid&2=ham&3=baz',  # invalid command name
        '0=foo&1=whois&2=ham&3=baz&spam=eggs',  # extra param
        '0=spam&1=whois&2=ham&3=eggs',  # invalid arg
        '0=spam&1=whois&2=ham&3=Serge2%09127.0.0.299',  # invalid ip
    )

    def setUp(self):
        super(WhoisApiTestCase, self).setUp()
        (models.ISP.objects
            .create(name='localhost', country='un')
            .ip_set.create(range_from=utils.force_ipy('127.0.0.0').int(), range_to=utils.force_ipy('127.0.0.255').int())
        )
        self.server = models.Server.objects.create(ip='127.0.0.1', port=10480, enabled=True, streamed=True)
        models.Game.objects.create(server=self.server)

    def test_valid_data_passed_to_whois_api_is_validated(self):
        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertEqual(force_text(response.content)[0], '0', qs)

            cache.clear()

    def test_invalid_data_passed_to_whois_api_is_not_validated(self):
        for qs in self.invalid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertEqual(force_text(response.content)[0], '1', qs)

            cache.clear()

    def test_unregistered_server_is_not_permitted_to_use_whois_api(self):
        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='192.168.1.125')
            self.assertEqual(force_text(response.content)[0], '1', qs)

            cache.clear()

    def test_unstreamed_server_is_not_permitted_to_use_whois_api(self):
        models.Server.objects.create(ip='127.0.0.5', port=10480, enabled=True, streamed=False)

        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.5')
            self.assertEqual(force_text(response.content)[0], '1', qs)

            cache.clear()

    def test_streamed_server_with_no_games_is_not_permitted_to_use_whois_api(self):
        server = models.Server.objects.create(ip='127.0.0.5', port=10480, enabled=True, streamed=True)

        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.5')
            self.assertEqual(force_text(response.content)[0], '1', qs)

            cache.clear()

    def test_streamed_server_with_no_recent_games_is_not_permitted_to_use_whois_api(self):
        server = models.Server.objects.create(ip='127.0.0.5', port=10480, enabled=True, streamed=True)
        # real now
        now = timezone.now()

        with patch.object(timezone, 'now') as mock:
            mock.return_value = now - datetime.timedelta(days=8)
            models.Game.objects.create(server=server)

        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.5')
            self.assertEqual(force_text(response.content)[0], '1', qs)

            cache.clear()

    def test_streamed_server_with_recently_finished_games_is_permitted_to_use_whois_api(self):
        server = models.Server.objects.create(ip='127.0.0.5', port=10480, enabled=True, streamed=True)
        # real now
        now = timezone.now()

        with patch.object(timezone, 'now') as mock:
            mock.return_value = now - datetime.timedelta(hours=23)
            models.Game.objects.create(server=server)

        for qs in self.valid_qs:
            response = self.client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.5')
            self.assertEqual(force_text(response.content)[0], '0', qs)

            cache.clear()
