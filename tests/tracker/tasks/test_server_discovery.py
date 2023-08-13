from django.test import override_settings

from apps.tracker.models import Server
from apps.tracker.tasks import discover_published_servers
from tests.factories.tracker import ServerFactory
from tests.factories.query import ServerQueryFactory


def test_server_discovery(db, create_httpservers, create_udpservers):
    with create_httpservers(2) as http_servers, create_udpservers(5) as udp_servers:
        server1, server2, server3, server4, server5 = udp_servers

        disabled_server = ServerFactory(
            ip=server1.address.ip, port=server1.address.port, enabled=False, listed=True, failures=8
        )
        unlisted_server = ServerFactory(
            ip=server2.address.ip,
            port=server2.address.port,
            enabled=True,
            listed=False,
            failures=15,
        )
        listed_server = ServerFactory(
            ip=server3.address.ip, port=server3.address.port, enabled=True, listed=True, failures=5
        )

        html_server, plain_server = http_servers
        sources = (
            {
                "url": html_server.url,
                "parser": "apps.tracker.discovery.html_ip_port",
            },
            {
                "url": plain_server.url,
                "parser": "apps.tracker.discovery.plain_ip_port",
            },
        )
        html_content = f"""<html>
        <ul>
            <li><span>{server1.address.ip}</span>:<span>{server1.address.port}</span></li>
            <li><span>{server2.address.ip}</span>:<span>{server2.address.port}</span></li>
            <li><span>{server1.address.ip}</span>:<span>0</span></li>
            <li><span>{server5.address.ip}</span>:<span>{server5.address.port}</span></li>
        </ul>
        </html>"""
        plain_content = f"""
        {server2.address.ip}:{server2.address.port}
        {server3.address.ip}:{server3.address.port}
        {server3.address.ip}:0
        {server4.address.ip}:{server4.address.port}
        """

        server1.responses.append(ServerQueryFactory(hostport=server1.address.port).as_gamespy())
        server2.responses.append(ServerQueryFactory(hostport=server2.address.port).as_gamespy())
        server3.responses.append(ServerQueryFactory(hostport=server3.address.port).as_gamespy())
        server4.responses.append(
            ServerQueryFactory(hostport=server4.address.port - 10).as_gamespy()
        )
        server5.responses.append(ServerQueryFactory(hostport=server5.address.port).as_gamespy())

        with override_settings(TRACKER_SERVER_DISCOVERY_SOURCES=sources):
            html_server.serve_content(html_content)
            plain_server.serve_content(plain_content)
            discover_published_servers()

    assert Server.objects.count() == 4

    disabled_server.refresh_from_db()
    assert not disabled_server.enabled
    assert disabled_server.listed
    assert disabled_server.failures == 8

    unlisted_server.refresh_from_db()
    assert unlisted_server.listed
    assert unlisted_server.failures == 0

    listed_server.refresh_from_db()
    assert listed_server.listed
    assert listed_server.failures == 5

    new_server = Server.objects.get(ip=server5.address.ip, port=server5.address.port)
    assert new_server.status_port == server5.address.query_port
    assert new_server.enabled
    assert new_server.listed
    assert new_server.failures == 0


def test_no_servers_discovered(db, create_httpservers):
    with create_httpservers(2) as servers:
        sources = (
            {
                "url": servers[0].url,
                "parser": "apps.tracker.discovery.plain_ip_port",
            },
            {
                "url": servers[1].url,
                "parser": "apps.tracker.discovery.html_ip_port",
            },
        )
        with override_settings(TRACKER_SERVER_DISCOVERY_SOURCES=sources):
            servers[0].serve_content(b"")
            servers[0].serve_content(b"server error", code=503)
            discover_published_servers()

    assert Server.objects.count() == 0


def test_target_responds_with_error_code(db, create_httpservers, create_udpservers):
    with create_udpservers(2) as udp_servers, create_httpservers(2) as http_servers:
        qs1, qs2 = udp_servers
        qs1.responses.append(ServerQueryFactory(hostport=qs1.address.port).as_gamespy())
        qs2.responses.append(ServerQueryFactory(hostport=qs2.address.port).as_gamespy())
        csv_content = f"{qs1.address.ip},{qs1.address.port}\n{qs2.address.ip},{qs2.address.port}"
        sources = (
            {
                "url": http_servers[0].url,
                "parser": "apps.tracker.discovery.html_ip_port",
            },
            {
                "url": http_servers[1].url,
                "parser": "apps.tracker.discovery.csv_two_columns",
            },
        )
        with override_settings(TRACKER_SERVER_DISCOVERY_SOURCES=sources):
            http_servers[0].serve_content("Server error", 500)
            http_servers[1].serve_content(csv_content)
            discover_published_servers()

        assert Server.objects.count() == 2
        assert Server.objects.get(
            ip=qs1.address.ip, port=qs1.address.port, status_port=qs1.address.query_port
        )
        assert Server.objects.get(
            ip=qs2.address.ip, port=qs2.address.port, status_port=qs2.address.query_port
        )
