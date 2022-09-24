import contextlib
import socketserver
import threading
import asyncio
from unittest import mock

from django.db import transaction
import pytest
from pytest_localserver.http import ContentServer
from rest_framework.test import APIClient
from ipwhois import IPWhois

from apps.tracker.utils.aio import with_timeout


@pytest.fixture(scope='session', autouse=True)
def _patch_on_commit_hook():
    old_on_commit = transaction.on_commit
    transaction.on_commit = lambda func, *args, **kwargs: func()
    yield
    transaction.on_commit = old_on_commit


@pytest.fixture(scope='session', autouse=True)
def _patch_replica_cursor(django_db_setup):
    from django.db import connections
    cursor = connections['default'].cursor
    connections['replica'].close()
    connections['replica'].cursor = cursor
    yield
    connections.close_all()


@pytest.fixture(autouse=True)
def whois_mock():
    with mock.patch.object(IPWhois, 'lookup_whois') as whois_mock_obj:
        whois_mock_obj.return_value = {'nets': [{'description': 'Test ISP',
                                                 'country': 'US',
                                                 'cidr': '1.2.0.0/16'}]}
        yield whois_mock_obj


@pytest.fixture
def create_httpservers():
    @contextlib.contextmanager
    def create(num_servers):
        servers = []
        for _ in range(num_servers):
            server = ContentServer()
            server.daemon = True
            servers.append(server)
        for server in servers:
            server.start()
        yield servers
        for server in servers:
            server.stop()
    return create


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def web_client():
    from django.test import Client
    return Client()


@pytest.fixture
def redis():
    from django_redis import get_redis_connection
    return get_redis_connection()


@pytest.fixture(autouse=True)
def caches():
    """
    Clear the django caches specified in settings.CACHES

    This is a workaround all test instances are
    NOT running in isolation and share same redis, so we clean up cache before we start
    """
    from django.conf import settings
    from django.core.cache import caches

    yield caches

    for alias in settings.CACHES:
        caches[alias].client.get_client().flushdb()


@pytest.fixture
def udp_server(request, create_udpservers):
    """Yield a single instance UDP server"""
    with create_udpservers(1) as servers:
        server = servers[0]
        if hasattr(request, 'cls') and request.cls:
            request.cls.udp_server = server
        yield server


@pytest.fixture
def create_udpservers():
    """
    Yield a generator to create a variable number of udp servers
    """
    @contextlib.contextmanager
    def create(num_servers):
        servers = []
        for _ in range(num_servers):
            servers.append(UDPServer())
        for server in servers:
            server.start()
        yield servers
        for server in servers:
            server.stop()
    return create


class UDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):

    def __init__(self, server_address=None, responses=None):
        self.responses = responses or []
        server_address = server_address or ('127.0.0.1', 0)
        super().__init__(server_address, None)

    def finish_request(self, request, client_address):
        responses = self.responses or [b'']
        packet, self.socket = request
        while responses:
            try:
                response = responses.pop()
            except IndexError:
                break
            self.socket.sendto(response, client_address)

    def start(self):
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print('started server %s with thread %s' % (self, self.thread))  # noqa

    def stop(self):
        self.shutdown()
        self.server_close()
        print('closed server %s with thread %s' % (self, self.thread))  # noqa


@pytest.fixture
def send_udp_query(loop):

    class UdpQueryProtocol:

        def __init__(self, message, loop):
            self.message = message
            self.loop = loop
            self.transport = None
            self.response = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)

        def connection_lost(self, exc):
            pass

        def datagram_received(self, data, addr):
            self.response = data
            self.transport.close()

        @with_timeout(1)
        async def wait_data(self):
            while True:
                if self.response is not None:
                    return self.response
                await asyncio.sleep(0.1)

    async def sender(addr, data):
        connect = loop.create_datagram_endpoint(lambda: UdpQueryProtocol(data, loop), remote_addr=addr)
        transport, protocol = await connect
        local_addr = transport.get_extra_info('socket').getsockname()
        return (await protocol.wait_data(), local_addr)

    return sender


@pytest.fixture
def send_tcp_query(loop):

    async def sender(addr, data):
        ip, port = addr
        reader, writer = await asyncio.open_connection(ip, port, loop=loop)
        writer.write(data)
        data = await reader.read(4096)
        writer.close()
        return data

    return sender
