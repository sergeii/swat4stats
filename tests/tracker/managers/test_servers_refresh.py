from apps.tracker.models import Server
from tests.factories.query import ServerQueryFactory
from tests.factories.tracker import ServerFactory


def test_queryset_refresh_status(db, create_udpservers):
    with create_udpservers(3) as udp_servers:
        servers = []
        for udp_server in udp_servers:
            server_ip, server_port = udp_server.server_address
            servers.append(ServerFactory(ip=server_ip, port=server_port - 1))

        failed_server, vip_server, coop_server = udp_servers
        failed_server.responses.append(b"")
        vip_server.responses.append(
            ServerQueryFactory(
                gametype="VIP Escort",
                hostname="-==MYT Team Svr==-",
                hostport=vip_server.server_address[1] - 1,
                with_players_count=15,
            ).as_gamespy()
        )
        coop_server.responses.append(
            ServerQueryFactory(
                gametype="CO-OP",
                hostname="-==MYT Co-Op Svr==-",
                hostport=coop_server.server_address[1] - 1,
                with_players_count=4,
            ).as_gamespy()
        )

        status, errors = Server.objects.refresh_status(*servers)
        assert len(status) == 2
        assert len(errors) == 1

        obj, result = errors[0]
        assert obj == servers[0]
        assert isinstance(result, Exception)

        obj, result = status[0]
        assert obj == servers[1]
        assert result["hostname"] == "-==MYT Team Svr==-"
        assert result["gametype"] == "VIP Escort"
        assert len(result["players"]) == 15

        obj, result = status[1]
        assert obj == servers[2]
        assert result["hostname"] == "-==MYT Co-Op Svr==-"
        assert result["gametype"] == "CO-OP"
        assert len(result["players"]) == 4

    servers_with_status = Server.objects.order_by("-pk").with_status()
    assert isinstance(servers_with_status, list)
    assert len(servers_with_status) == 2

    assert servers_with_status[0].pk == servers[2].pk
    assert servers_with_status[0].status["hostname"] == "-==MYT Co-Op Svr==-"

    assert servers_with_status[1].pk == servers[1].pk
    assert servers_with_status[1].status["hostname"] == "-==MYT Team Svr==-"


def test_negative_timers_are_supported(db, udp_server):
    server_ip, server_query_port = udp_server.server_address
    server_join_port = server_query_port - 1
    server = ServerFactory(ip=server_ip, port=server_join_port)

    udp_server.responses.append(
        ServerQueryFactory(
            gametype="VIP Escort",
            hostname="-==MYT Team Svr==-",
            hostport=server_join_port,
            timespecial="-1",
            timeleft="-1",
        ).as_gamespy()
    )

    status, errors = Server.objects.refresh_status(server)
    assert len(status) == 1
    assert len(errors) == 0

    obj, result = status[0]
    assert result["hostname"] == "-==MYT Team Svr==-"
    assert result["gametype"] == "VIP Escort"
    assert result["timeleft"] is None
    assert result["timespecial"] is None
