from datetime import datetime
from functools import partial
from unittest import mock

import pytest
import pytz
from django.conf import settings

from apps.tracker.models import Server
from apps.tracker.signals import failed_servers_detected, live_servers_detected
from apps.tracker.tasks import refresh_listed_servers
from apps.utils.test import freeze_timezone_now
from tests.factories.query import ServerQueryFactory
from tests.factories.tracker import ServerFactory


@freeze_timezone_now(datetime(2023, 8, 11, 18, 44, 11, tzinfo=pytz.UTC))
@pytest.mark.parametrize(
    "current_hostname_updated_at",
    [
        None,
        datetime(2022, 8, 1, 11, 22, 33, tzinfo=pytz.UTC),
    ],
)
@pytest.mark.parametrize(
    "raw_hostname, clean_hostname",
    [
        ("New Hostname", "New Hostname"),
        ("[C=FFFFFF][b][u]Fancy Hostname[/u][/b][/C]", "Fancy Hostname"),
        ("", ""),
    ],
)
def test_hostname_is_updated_for_active_servers(
    now_mock,
    db,
    create_udpservers,
    current_hostname_updated_at,
    raw_hostname,
    clean_hostname,
):
    with create_udpservers(1) as udp_servers:
        udp_server = udp_servers[0]
        server_ip, server_port = udp_server.server_address
        udp_server.responses.append(
            ServerQueryFactory(hostport=server_port - 1, hostname=raw_hostname).as_gamespy()
        )
        server = ServerFactory(
            ip=server_ip,
            port=server_port - 1,
            hostname="Old Hostname",
            hostname_updated_at=current_hostname_updated_at,
            listed=True,
        )
        refresh_listed_servers.delay()

    server.refresh_from_db()
    assert server.hostname == raw_hostname
    assert server.hostname_clean == clean_hostname
    assert server.hostname_updated_at == datetime(2023, 8, 11, 18, 44, 11, tzinfo=pytz.UTC)


def test_server_status_signals_are_invoked(db, create_udpservers):
    with create_udpservers(5) as udp_servers:
        servers = []
        udp_servers[0].responses.append(
            ServerQueryFactory(hostport=udp_servers[0].server_address[1] - 1).as_gamespy()
        )
        udp_servers[1].responses.append(
            ServerQueryFactory(hostport=udp_servers[1].server_address[1] - 1).as_gamespy()
        )
        udp_servers[2].responses.append(b"")
        udp_servers[3].responses.append(
            ServerQueryFactory(hostport=udp_servers[3].server_address[1] - 1).as_gamespy()
        )
        udp_servers[4].responses.append(b"")

        for udp_server in udp_servers:
            server_ip, server_port = udp_server.server_address
            servers.append(ServerFactory(ip=server_ip, port=server_port - 1, listed=True))

        create_live_mock = partial(
            mock.patch.object, live_servers_detected, "send", wraps=live_servers_detected.send
        )
        create_failed_mock = partial(
            mock.patch.object, failed_servers_detected, "send", wraps=failed_servers_detected.send
        )

        failing_server = servers[-1]
        failing_server.failures = settings.TRACKER_STATUS_TOLERATED_FAILURES - 1
        failing_server.save()

        with (
            create_live_mock() as live_mock,
            create_failed_mock() as failed_mock,
        ):
            refresh_listed_servers.delay()

            assert live_mock.called
            _, kwargs = live_mock.call_args
            assert {obj.pk for obj in kwargs["servers"]} == {
                servers[0].pk,
                servers[1].pk,
                servers[3].pk,
            }

            assert failed_mock.called
            _, kwargs = failed_mock.call_args
            assert {obj.pk for obj in kwargs["servers"]} == {servers[2].pk, servers[4].pk}

        assert Server.objects.filter(pk__in=[servers[2].pk], failures=1).count() == 1
        assert (
            Server.objects.filter(
                pk__in=[servers[4].pk], failures=settings.TRACKER_STATUS_TOLERATED_FAILURES
            ).count()
            == 1
        )
        assert (
            Server.objects.filter(
                pk__in=[servers[0].pk, servers[1].pk, servers[3].pk], failures=0
            ).count()
            == 3
        )


def test_failure_count_is_incremented_for_failing_servers(db, create_udpservers):
    with create_udpservers(3) as udp_servers:
        server1_ip, server1_port = udp_servers[0].server_address
        server2_ip, server2_port = udp_servers[1].server_address
        server1 = ServerFactory(ip=server1_ip, port=server1_port - 1, listed=True, failures=1)
        server2 = ServerFactory(ip=server2_ip, port=server2_port - 1, listed=True, failures=0)

        refresh_listed_servers.delay()

        server1.refresh_from_db()
        server2.refresh_from_db()

        assert server1.failures == 2
        assert server1.listed
        assert server2.failures == 1
        assert server2.listed


def test_failure_count_is_reset_for_active_servers(db, udp_server):
    server_ip, udp_port = udp_server.server_address
    udp_server.responses.append(ServerQueryFactory(hostport=udp_port - 1).as_gamespy())

    server = ServerFactory(
        ip=server_ip, port=udp_port - 1, status_port=udp_port, listed=True, failures=13
    )
    unlisted = ServerFactory(listed=False, failures=15)

    refresh_listed_servers.delay()

    server.refresh_from_db()
    unlisted.refresh_from_db()

    assert server.failures == 0
    assert unlisted.failures == 15
