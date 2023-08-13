from datetime import datetime
from unittest import mock

import pytest
import pytz

from apps.tracker.models import Server
from apps.tracker.signals import (
    failed_servers_detected,
    live_servers_detected,
)
from apps.tracker.tasks import refresh_listed_servers
from apps.utils.test import freeze_timezone_now
from tests.factories.geoip import ISPFactory
from tests.factories.tracker import ServerFactory, ListedServerFactory
from tests.factories.query import ServerQueryFactory


@pytest.fixture
def server(db):
    return ServerFactory(hostname="foo", country="cy", hostname_updated_at=None)


@freeze_timezone_now(datetime(2023, 8, 11, 18, 44, 11, tzinfo=pytz.UTC))
def test_hostname_is_updated_if_new(now_mock, server):
    servers = {server: {"hostname": "bar"}}
    live_servers_detected.send(sender=None, servers=servers)

    server.refresh_from_db()
    assert server.hostname == "bar"
    assert server.hostname_updated_at == datetime(2023, 8, 11, 18, 44, 11, tzinfo=pytz.UTC)


@freeze_timezone_now(datetime(2023, 8, 11, 18, 44, 11, tzinfo=pytz.UTC))
def test_hostname_not_updated_if_not_changed(now_mock, server):
    servers = {server: {"hostname": "foo"}}

    with mock.patch.object(Server, "save") as save_mock:
        live_servers_detected.send(sender=None, servers=servers)
        assert not save_mock.called

    server.refresh_from_db()
    assert server.hostname == "foo"
    assert server.hostname_updated_at is None


def test_live_server_failure_count_is_reset(server, udp_server):
    server_ip, server_port = udp_server.server_address
    server = ServerFactory(ip=server_ip, port=server_port - 1, failures=10, listed=True)
    ISPFactory(country="uk", ip=server_ip)
    udp_server.responses.append(ServerQueryFactory(hostport=server_port - 1).as_gamespy())

    refresh_listed_servers.delay()
    server.refresh_from_db()
    assert server.failures == 0
    assert server.listed


def test_failure_count_is_incremented_server_stays_listed(db):
    server1, server2 = [
        ListedServerFactory(failures=0),
        ListedServerFactory(failures=10),
    ]
    failed_servers_detected.send(sender=None, servers=[server1, server2])

    assert Server.objects.get(pk=server1.pk, failures=1, listed=True)
    assert Server.objects.get(pk=server2.pk, failures=11, listed=True)
