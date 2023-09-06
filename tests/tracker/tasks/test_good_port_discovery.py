from apps.tracker.tasks import discover_good_query_ports
from tests.factories.query import ServerQueryFactory
from tests.factories.tracker import ServerFactory


def test_discover_good_query_ports(db, create_udpservers):
    with create_udpservers(2) as udp_servers:
        qs1, qs2 = udp_servers
        server1 = ServerFactory(
            ip=qs1.address.ip,
            port=qs1.address.port,
            listed=True,
            status_port=qs1.address.query_port + 2,
        )
        server2 = ServerFactory(
            ip=qs2.address.ip, port=qs2.address.port, listed=True, status_port=1234
        )
        offline_server = ServerFactory(ip=qs2.address.ip, port=1000, status_port=1001, listed=True)
        unlisted_server = ServerFactory(listed=False)  # noqa: F841
        qs1.responses.append(ServerQueryFactory(hostport=qs1.address.port, swatwon=0).as_gamespy())
        qs2.responses.append(ServerQueryFactory(hostport=qs2.address.port).as_gamespy())
        discover_good_query_ports()

        server1.refresh_from_db()
        server2.refresh_from_db()
        offline_server.refresh_from_db()
        assert server1.status_port == qs1.address.query_port
        assert server2.status_port == qs2.address.query_port
        assert offline_server.status_port == 1001
        assert offline_server.failures == 0
