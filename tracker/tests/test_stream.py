from __future__ import unicode_literals

from mock import patch, PropertyMock
from julia import node
from hashlib import md5

from django import test

from tracker import models


def encode_post_data(d):
    return '&'.join(['%s=%s' % (key, value) for key, value in d.items()])


class StreamTestCase(test.TestCase):

    def setUp(self):
        self.client = test.Client(enforce_csrf_checks=True, REMOTE_ADDR='127.0.0.1')

        self.test_qs = {
            '0': 'tag', 
            '1': '1.0.0', 
            '2': '10480', 
            '3': '1401335782', 
            '4': md5(b'key104801401335782').hexdigest()[-8:],
            '5': '0',
            '6': '1.1',
            '7': 'test',
            '8': '1',
            '11': '14',
            '12': '16',
            '14': '5',
            '15': '160',
            '16': '160',
            '17': '900',
            '22': '6',
        }
        self.test_data = encode_post_data(self.test_qs)

    def test_stream_post_method_bypasses_csrf_check(self):
        response = self.client.post('/stream/', encode_post_data({'foo': 'bar'}), content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

    def test_streamed_server(self):
        models.Server.objects.create(ip='127.0.0.1', port=10480, enabled=True, streamed=True)

        response = self.client.post('/stream/', self.test_data, content_type='application/x-www-form-urlencoded')
        self.assertEqual(chr(response.content[0]), '0')

    def test_unstreamed_server(self):
        models.Server.objects.create(ip='127.0.0.1', port=10480, enabled=True, streamed=False)

        response = self.client.post('/stream/', self.test_data, content_type='application/x-www-form-urlencoded')
        self.assertNotEqual(chr(response.content[0]), '0')
