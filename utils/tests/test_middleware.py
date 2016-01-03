from django.test import TestCase


class ClientIpMiddlewareTestCase(TestCase):

    def test_client_ip_overwrites_remote_addr(self):
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1', X_CLIENT_IP='1.1.1.1')
        assert response.wsgi_request.META['REMOTE_ADDR'] == '1.1.1.1'

    def test_remote_addr_is_retained(self):
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1')
        assert response.wsgi_request.META['REMOTE_ADDR'] == '127.0.0.1'
