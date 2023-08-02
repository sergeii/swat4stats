from unittest import mock

import pytest

from apps.geoip.factories import ISPFactory
from apps.tracker.factories import ServerFactory, ListedServerFactory, ServerQueryFactory
from apps.tracker.models import Server
from apps.tracker.signals import (
    failed_servers_detected,
    offline_servers_detected,
    live_servers_detected,
)
from apps.tracker.tasks import refresh_listed_servers


@pytest.fixture
def server(db):
    return ServerFactory(hostname="foo", country="cy")


def test_hostname_is_updated_if_new(server):
    servers = {server: {"hostname": "bar"}}
    live_servers_detected.send(sender=None, servers=servers)
    server.refresh_from_db()
    assert server.hostname == "bar"


def test_hostname_not_updated_if_not_changed(server):
    servers = {server: {"hostname": "foo"}}
    with mock.patch.object(Server, "save") as save_mock:
        live_servers_detected.send(sender=None, servers=servers)
        assert not save_mock.called
    server.refresh_from_db()
    assert server.hostname == "foo"


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


def test_offline_servers_detected_is_called_if_hit_failure_limit(db):
    offline_server, failed_server = [
        ListedServerFactory(failures=11),
        ListedServerFactory(failures=10),
    ]
    with mock.patch.object(
        offline_servers_detected, "send", wraps=offline_servers_detected.send
    ) as signal_mock:
        failed_servers_detected.send(sender=None, servers=[offline_server, failed_server])
        call_args = signal_mock.call_args[1]
        assert list(call_args["servers"]) == [offline_server]

    offline_server.refresh_from_db()
    failed_server.refresh_from_db()
    assert not offline_server.listed
    assert offline_server.failures == 12
    assert failed_server.listed
    assert failed_server.failures == 11


def test_offline_servers_are_unlisted_failure_count_not_reset(db):
    servers = [
        ListedServerFactory(failures=0),
        ListedServerFactory(failures=2),
        ServerFactory(failures=4, listed=False),
    ]
    offline_servers_detected.send(sender=None, servers=servers)
    assert Server.objects.get(pk=servers[0].pk, failures=0, listed=False)
    assert Server.objects.get(pk=servers[1].pk, failures=2, listed=False)
    assert Server.objects.get(pk=servers[2].pk, failures=4, listed=False)


def test_offline_servers_are_removed_from_redis(db, redis):
    servers = [
        ServerFactory(ip="10.20.30.40", port=10480),
        ServerFactory(ip="10.20.30.40", port=10580),
        ServerFactory(ip="1.2.3.4", port=10480),
    ]
    redis.hmset(
        "servers", {"10.20.30.40:10480": "{}", "10.20.30.40:10580": "{}", "10.20.30.40:10680": "{}"}
    )
    offline_servers_detected.send(sender=None, servers=servers)

    assert list(redis.hgetall("servers")) == [b"10.20.30.40:10680"]
