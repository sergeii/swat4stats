from django.test import override_settings

from settings.common import re_ipv4, re_port
from apps.tracker.factories import ServerFactory, ServerQueryFactory
from apps.tracker.models import Server
from apps.tracker.tasks import discover_servers, discover_extra_query_ports


class QueryServerAddress:

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


def test_server_discovery(db, create_httpservers, create_udpservers):
    with create_httpservers(2) as http_servers, create_udpservers(4) as udp_servers:
        server1, server2, server3, server4 = udp_servers
        server1_addr, server2_addr, server3_addr, server4_addr = map(QueryServerAddress, udp_servers)

        disabled_server = ServerFactory(ip=server1_addr.ip, port=server1_addr.port,
                                        enabled=False, listed=True, failures=8)
        unlisted_server = ServerFactory(ip=server2_addr.ip, port=server2_addr.port,
                                        enabled=True, listed=False, failures=15)
        listed_server = ServerFactory(ip=server3_addr.ip, port=server3_addr.port,
                                      enabled=True, listed=True, failures=5)

        html_server, plain_server = http_servers
        targets = (
            (html_server.url, fr'\b(?P<addr>{re_ipv4})[^:]*:[^\d]*(?P<port>{re_port})\b'),
            (plain_server.url, fr'(?P<addr>{re_ipv4}):(?P<port>{re_port})'),
        )
        html_content = f"""<html>
        <ul>
            <li><span>{server1_addr.ip}</span>:<span>{server1_addr.port}</span></li>
            <li><span>{server2_addr.ip}</span>:<span>{server2_addr.port}</span></li>
            <li><span>{server1_addr.ip}</span>:<span>0</span></li>
        </ul>
        </html>"""
        plain_content = f"""
        {server2_addr.ip}:{server2_addr.port}
        {server3_addr.ip}:{server3_addr.port}
        {server3_addr.ip}:0
        {server4_addr.ip}:{server4_addr.port}
        """

        server1.responses.append(ServerQueryFactory(hostport=server1_addr.port).as_gamespy())
        server2.responses.append(ServerQueryFactory(hostport=server2_addr.port).as_gamespy())
        server3.responses.append(ServerQueryFactory(hostport=server3_addr.port).as_gamespy())
        server4.responses.append(ServerQueryFactory(hostport=server4_addr.port - 10).as_gamespy())

        with override_settings(TRACKER_SERVER_DISCOVERY=targets):
            html_server.serve_content(html_content)
            plain_server.serve_content(plain_content)
            discover_servers()

    assert Server.objects.count() == 3

    disabled_server.refresh_from_db()
    assert not disabled_server.enabled
    assert disabled_server.listed
    assert disabled_server.failures == 8

    unlisted_server.refresh_from_db()
    assert unlisted_server.listed
    assert unlisted_server.failures == 0

    listed_server.refresh_from_db()
    assert listed_server.listed
    assert listed_server.failures == 0

    new_server = Server.objects.get(ip=server3_addr.ip, port=server3_addr.port)
    assert new_server.status_port == server3_addr.query_port
    assert new_server.enabled
    assert new_server.listed
    assert new_server.failures == 0


def test_no_servers_discovered(db, create_httpservers):
    with create_httpservers(2) as servers:
        targets = (
            (servers[0].url, fr'\b(?P<addr>{re_ipv4})[^:]*:[^\d]*(?P<port>{re_port})\b'),
            (servers[1].url, fr'\b(?P<addr>{re_ipv4})[^:]*:[^\d]*(?P<port>{re_port})\b'),
        )
        with override_settings(TRACKER_SERVER_DISCOVERY=targets):
            servers[0].serve_content(b'')
            servers[0].serve_content(b'server error', code=503)
            discover_servers()

    assert Server.objects.count() == 0


def test_target_responds_with_error_code(db, create_httpservers, create_udpservers):
    with create_udpservers(2) as udp_servers, create_httpservers(2) as http_servers:
        query_server1, query_server2 = udp_servers
        server_addr1 = QueryServerAddress(query_server1)
        server_addr2 = QueryServerAddress(query_server2)
        query_server1.responses.append(ServerQueryFactory(hostport=server_addr1.port).as_gamespy())
        query_server2.responses.append(ServerQueryFactory(hostport=server_addr2.port).as_gamespy())
        csv_content = f"""
        {server_addr1.ip},{server_addr1.port}
        {server_addr2.ip},{server_addr2.port}
        """
        targets = (
            (http_servers[0].url, fr'\b(?P<addr>{re_ipv4})[^:]*:[^\d]*(?P<port>{re_port})\b'),
            (http_servers[1].url, fr'(?P<addr>{re_ipv4}),(?P<port>{re_port})'),
        )
        with override_settings(TRACKER_SERVER_DISCOVERY=targets):
            http_servers[0].serve_content('Server error', 500)
            http_servers[1].serve_content(csv_content)
            discover_servers()

        assert Server.objects.count() == 2
        assert Server.objects.get(ip=server_addr1.ip, port=server_addr1.port, status_port=server_addr1.query_port)
        assert Server.objects.get(ip=server_addr1.ip, port=server_addr2.port, status_port=server_addr2.query_port)


def test_discover_extra_query_ports(db, create_udpservers):
    with create_udpservers(2) as udp_servers:
        query_server1, query_server2 = udp_servers
        server_addr1 = QueryServerAddress(query_server1)
        server_addr2 = QueryServerAddress(query_server2)
        server1 = ServerFactory(ip=server_addr1.ip,
                                port=server_addr1.port,
                                listed=True,
                                status_port=server_addr1.query_port + 2)
        server2 = ServerFactory(ip=server_addr2.ip,
                                port=server_addr2.port,
                                listed=True,
                                status_port=1234)
        offline_server = ServerFactory(ip=server_addr2.ip,
                                       port=1000,
                                       status_port=1001,
                                       listed=True)
        unlisted_server = ServerFactory(listed=False)  # noqa
        query_server1.responses.append(ServerQueryFactory(hostport=server_addr1.port, swatwon=0).as_gamespy())
        query_server2.responses.append(ServerQueryFactory(hostport=server_addr2.port).as_gamespy())
        discover_extra_query_ports()

        server1.refresh_from_db()
        server2.refresh_from_db()
        offline_server.refresh_from_db()
        assert server1.status_port == server_addr1.query_port
        assert server2.status_port == server_addr2.query_port
        assert offline_server.status_port == 1001
        assert offline_server.failures == 0
