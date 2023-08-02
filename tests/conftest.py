import contextlib
import socketserver
import threading
from functools import cached_property
from collections.abc import Iterator
from unittest import mock

from django.db import transaction
import pytest
from pytest_localserver.http import ContentServer
from rest_framework.test import APIClient
from ipwhois import IPWhois


@pytest.fixture(scope="session", autouse=True)
def _enable_celery_eager_mode():
    from swat4stats.celery import app

    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def _configure_default_storage(settings):
    settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@pytest.fixture(autouse=True)
def _disable_debug(settings):
    settings.DEBUG = False


@pytest.fixture(scope="session", autouse=True)
def _patch_on_commit_hook():
    old_on_commit = transaction.on_commit
    transaction.on_commit = lambda func, *args, **kwargs: func()
    yield
    transaction.on_commit = old_on_commit


@pytest.fixture(scope="session", autouse=True)
def _patch_replica_cursor(django_db_setup):
    from django.db import connections

    cursor = connections["default"].cursor
    connections["replica"].close()
    connections["replica"].cursor = cursor
    yield
    connections.close_all()


@pytest.fixture(autouse=True)
def whois_mock():
    with mock.patch.object(IPWhois, "lookup_whois") as whois_mock_obj:
        whois_mock_obj.return_value = {
            "nets": [{"description": "Test ISP", "country": "US", "cidr": "1.2.0.0/16"}]
        }
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


@pytest.fixture
def site(db):
    from django.contrib.sites.models import Site

    return Site.objects.get_current()


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
        if hasattr(request, "cls") and request.cls:
            request.cls.udp_server = server
        yield server


@pytest.fixture
def create_udpservers():
    """
    Yield a generator to create a variable number of udp servers
    """

    @contextlib.contextmanager
    def create(num_servers: int) -> Iterator[list[UDPServer]]:
        servers = [UDPServer() for _ in range(num_servers)]
        for server in servers:
            server.start()
        yield servers
        for server in servers:
            server.stop()

    return create


class UDPServerAddress:
    def __init__(self, server):
        self.address = server.server_address

    @property
    def ip(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1] - 1

    @property
    def query_port(self):
        return self.address[1]


class UDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(
        self,
        server_address: tuple[str, int] | None = None,
        responses: list[bytes] | None = None,
    ) -> None:
        self.responses = responses or []
        server_address = server_address or ("127.0.0.1", 0)
        super().__init__(server_address, None, bind_and_activate=True)

    def finish_request(self, request, client_address):
        responses = self.responses or [b""]
        packet, self.socket = request
        while responses:
            try:
                response = responses.pop()
            except IndexError:
                break
            self.socket.sendto(response, client_address)

    def start(self) -> None:
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        self.shutdown()
        self.server_close()

    @cached_property
    def address(self) -> UDPServerAddress:
        return UDPServerAddress(self)
