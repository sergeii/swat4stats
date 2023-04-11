from functools import partial
from unittest import mock

from django.conf import settings

from apps.tracker.factories import ServerFactory, ServerQueryFactory
from apps.tracker.models import Server
from apps.tracker.signals import live_servers_detected, offline_servers_detected, failed_servers_detected
from apps.tracker.tasks import refresh_listed_servers


# def test_refresh_listed_servers(db):
#     unlisted_servers = ServerFactory.create_batch(2, listed=False)  # noqa
#     listed_servers = ServerFactory.create_batch(3, listed=True)
#
#     with mock.patch.object(refresh_servers_chunk, 'apply_async') as refresh_mock:
#         refresh_listed_servers.delay()
#         assert refresh_mock.called
#         args, kwargs = refresh_mock.call_args[0]
#         assert set(args) == {obj.pk for obj in listed_servers}


def test_hostname_is_updated_for_active_servers(db, create_udpservers):
    with create_udpservers(1) as udp_servers:
        udp_server = udp_servers[0]
        server_ip, server_port = udp_server.server_address
        udp_server.responses.append(ServerQueryFactory(hostport=server_port-1, hostname='New Hostname').as_gamespy())
        server = ServerFactory(ip=server_ip, port=server_port-1, hostname='Old Hostname', listed=True)
        refresh_listed_servers.delay()
    server.refresh_from_db()
    assert server.hostname == 'New Hostname'


def test_server_status_signals_are_invoked(db, create_udpservers):
    with create_udpservers(5) as udp_servers:
        servers = []
        udp_servers[0].responses.append(ServerQueryFactory(hostport=udp_servers[0].server_address[1]-1).as_gamespy())
        udp_servers[1].responses.append(ServerQueryFactory(hostport=udp_servers[1].server_address[1]-1).as_gamespy())
        udp_servers[2].responses.append(b'')
        udp_servers[3].responses.append(ServerQueryFactory(hostport=udp_servers[3].server_address[1]-1).as_gamespy())
        udp_servers[4].responses.append(b'')

        for udp_server in udp_servers:
            server_ip, server_port = udp_server.server_address
            servers.append(ServerFactory(ip=server_ip, port=server_port-1, listed=True))

        create_live_mock = partial(mock.patch.object, live_servers_detected, 'send',
                                   wraps=live_servers_detected.send)
        create_failed_mock = partial(mock.patch.object, failed_servers_detected, 'send',
                                     wraps=failed_servers_detected.send)
        create_offline_mock = partial(mock.patch.object, offline_servers_detected, 'send',
                                      wraps=offline_servers_detected.send)

        failing_server = servers[-1]
        failing_server.failures = settings.TRACKER_STATUS_TOLERATED_FAILURES - 1
        failing_server.save()

        with (
            create_live_mock() as live_mock,
            create_failed_mock() as failed_mock,
            create_offline_mock() as offline_mock
        ):
            refresh_listed_servers.delay()

            assert live_mock.called
            args, kwargs = live_mock.call_args
            assert {obj.pk for obj in kwargs['servers']} == {servers[0].pk, servers[1].pk, servers[3].pk}

            assert failed_mock.called
            args, kwargs = failed_mock.call_args
            assert {obj.pk for obj in kwargs['servers']} == {servers[2].pk, servers[4].pk}

            assert offline_mock.called
            args, kwargs = offline_mock.call_args
            assert {obj.pk for obj in kwargs['servers']} == {servers[4].pk}

        assert Server.objects.filter(pk__in=[servers[2].pk], failures=1).count() == 1
        assert Server.objects.filter(pk__in=[servers[4].pk],
                                     failures=settings.TRACKER_STATUS_TOLERATED_FAILURES).count() == 1
        assert Server.objects.filter(pk__in=[servers[0].pk, servers[1].pk, servers[3].pk], failures=0).count() == 3


def test_failure_count_is_incremented_for_failing_servers(db, create_udpservers):
    with create_udpservers(3) as udp_servers:
        server1_ip, server1_port = udp_servers[0].server_address
        server2_ip, server2_port = udp_servers[1].server_address
        server1 = ServerFactory(ip=server1_ip, port=server1_port-1, listed=True, failures=1)
        server2 = ServerFactory(ip=server2_ip, port=server2_port-1, listed=True, failures=0)

        refresh_listed_servers.delay()

        server1.refresh_from_db()
        server2.refresh_from_db()

        assert server1.failures == 2
        assert server1.listed
        assert server2.failures == 1
        assert server2.listed


def test_failure_count_is_reset_for_active_servers(db, udp_server):
    server_ip, udp_port = udp_server.server_address
    udp_server.responses.append(ServerQueryFactory(hostport=udp_port-1).as_gamespy())

    server = ServerFactory(ip=server_ip, port=udp_port-1, status_port=udp_port, listed=True, failures=13)
    unlisted = ServerFactory(listed=False, failures=15)

    refresh_listed_servers.delay()

    server.refresh_from_db()
    unlisted.refresh_from_db()

    assert server.failures == 0
    assert unlisted.failures == 15
