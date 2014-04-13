from __future__ import unicode_literals

from django import test

class StreamViewCase(test.TestCase):

    def test_stream_get_method(self):
        response = self.client.get('/stream/')
        self.assertEqual(response.status_code, 200)

    def test_stream_post_method_bypasses_csrf_check(self):
        c = test.Client(enforce_csrf_checks=True)
        response = c.post('/stream/', {'foo': 'bar'})
        self.assertEqual(response.status_code, 200)