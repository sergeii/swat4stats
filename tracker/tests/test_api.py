from __future__ import unicode_literals

from django import test
from cacheops import invalidation
from django.core.cache import cache

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

    def test_valid_data(self):
        client = test.Client()
        for qs in self.valid_qs:
            response = client.get('/api/whois/?%s' % qs)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertEqual(chr(response.content[0]), '0', qs)

            cache.clear()

    def test_invalid_data(self):
        client = test.Client()
        for qs in self.invalid_qs:
            response = client.get('/api/whois/?%s' % qs)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertNotEqual(chr(response.content[0]), '0', qs)

            cache.clear()

    def test_invalid_server(self):
        client = test.Client()
        for qs in self.valid_qs:
            response = client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.2')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertNotEqual(chr(response.content[0]), '0', qs)

            cache.clear()

    def test_unstreamed_server(self):
        models.Server.objects.create(ip='127.0.0.2', port=10480, enabled=True, streamed=False)

        client = test.Client()
        for qs in self.valid_qs:
            response = client.get('/api/whois/?%s' % qs, REMOTE_ADDR='127.0.0.2')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content)
            self.assertNotEqual(chr(response.content[0]), '0', qs)

            cache.clear()
