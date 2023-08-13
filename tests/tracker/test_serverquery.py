import asyncio
from collections import OrderedDict

import pytest

from apps.tracker.utils import aio
from apps.tracker.aio_tasks.serverquery import ServerStatusTask, ResponseMalformedError
from tests.factories.tracker import ServerFactory
from tests.factories.query import ServerQueryFactory


def query_servers(*addresses):
    result = OrderedDict([(query_address, None) for query_address in addresses])
    tasks = []

    def callback(query_address, status):
        result[query_address] = status

    for query_address in addresses:
        ip, status_port = query_address
        tasks.append(
            ServerStatusTask(
                callback=callback, result_id=query_address, ip=ip, status_port=status_port
            )
        )

    aio.run_many(tasks)
    return list(result.values())


@pytest.mark.django_db()
def test_serverquery_async_task_pool(create_udpservers):
    with create_udpservers(3) as udp_servers:
        result = {}
        servers = []
        tasks = []

        def callback(server, status):
            result[server] = status

        for udp_server in udp_servers:
            server_ip, server_port = udp_server.server_address
            server = ServerFactory(ip=server_ip, status_port=server_port)
            kwargs = {
                "ip": server.ip,
                "status_port": server.status_port,
            }
            tasks.append(ServerStatusTask(callback=callback, result_id=server, **kwargs))
            servers.append(server)

        udp_servers[0].responses.append(None)
        udp_servers[1].responses.append(b"")
        udp_servers[2].responses.append(
            ServerQueryFactory(
                hostname="-==MYT Team Svr==-", gametype="VIP Escort", with_players_count=15
            ).as_gamespy()
        )

        aio.run_many(tasks)

        assert isinstance(result[servers[0]], asyncio.TimeoutError)
        assert isinstance(result[servers[1]], ResponseMalformedError)
        assert isinstance(result[servers[2]], dict)

        status = result[servers[2]]
        assert status["hostname"] == "-==MYT Team Svr==-"
        assert status["gametype"] == "VIP Escort"
        assert len(status["players"]) == 15


def test_adminmod_serverquery_is_supported(udp_server):
    payload = [
        # last packet comes first and so forth
        b"\\statusresponse\\2\\kills_13\\1\\kills_14\\1\\deaths_1\\1\\deaths_2\\1\\deaths_4\\1\\deaths_5\\1"
        b"\\deaths_9\\1\\deaths_14\\1\\queryid\\AMv1\\final\\\\eof\\",
        # key, value of score_0 from statusresponse=0 have been split
        b"\\statusresponse\\1\\0\\score_1\\0\\score_2\\1\\score_3\\0\\score_4\\0\\score_5\\0\\score_6\\0"
        b"\\score_7\\0\\score_8\\1\\score_9\\0\\score_10\\0\\score_11\\0\\score_12\\2\\score_13\\1"
        b"\\score_14\\1\\ping_0\\155\\ping_1\\127\\ping_2\\263\\ping_3\\163\\ping_4\\111\\ping_5\\117\\ping_6"
        b"\\142\\ping_7\\121\\ping_8\\159\\ping_9\\142\\ping_10\\72\\ping_11\\154\\ping_12\\212\\ping_13"
        b"\\123\\ping_14\\153\\team_0\\1\\team_1\\0\\team_2\\1\\team_3\\0\\team_4\\0\\team_5\\0\\team_6\\1"
        b"\\team_7\\1\\team_8\\0\\team_9\\0\\team_10\\0\\team_11\\1\\team_12\\1\\team_13\\0\\team_14\\1"
        b"\\kills_2\\1\\kills_8\\1\\kills_12\\2\\eof\\",
        b"\\statusresponse\\0\\hostname\\{FAB} Clan Server\\numplayers\\15\\maxplayers"
        b"\\16\\gametype\\VIP Escort\\gamevariant\\SWAT 4\\mapname\\Red Library Offices"
        b"\\hostport\\10580\\password\\0\\gamever\\1.0\\statsenabled\\0\\swatwon\\1\\suspectswon\\0"
        b"\\round\\2\\numrounds\\7\\player_0\\{FAB}Nikki_Sixx<CPL>\\player_1\\Nico^Elite\\player_2"
        b"\\Balls\\player_3\\\xab|FAL|\xdc\xee\xee\xe4^\\player_4\\Reynolds\\player_5\\4Taws\\player_6"
        b"\\Daro\\player_7\\Majos\\player_8\\mi\\player_9\\tony\\player_10\\MENDEZ\\player_11\\ARoXDeviL"
        b"\\player_12\\{FAB}Chry<CPL>\\player_13\\P\\player_14\\xXx\\score_0\\eof\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["hostname"] == "{FAB} Clan Server"
    assert data["hostport"] == "10580"
    assert data["gametype"] == "VIP Escort"
    assert data["queryid"] == "AMv1"
    assert data["final"] == ""
    assert "statusresponse" not in data
    assert "eof" not in data
    assert data["players"][0]["score"] == "0"
    assert data["players"][3]["ping"] == "163"
    assert data["players"][3]["player"] == "«|FAL|Üîîä^"
    assert data["players"][12]["kills"] == "2"
    assert data["players"][13]["player"] == "P"

    payload = [
        b"\\statusresponse\\0\\hostname\\[C=FF0000][c=33CCCC]>|S[C=FFFFFF]S|<[c=ffff00]Arg[C=ffffff]en[c=33CCCC]tina\xae[c=ff0000]-By FNXgaming.com"  # noqa: E501
        b"\\numplayers\\10\\maxplayers\\16\\gametype\\Barricaded Suspects\\gamevariant\\SWAT 4\\"
        b"mapname\\A-Bomb Nightclub\\hostport\\10780\\password\\0\\gamever\\1.0\\statsenabled\\0\\swatwon\\2\\suspectswon\\0"  # noqa: E501
        b"\\round\\3\\numrounds\\3\\player_0\\darwinn\\player_1\\kyle\\player_2\\super\\player_3\\\xab|FAL|cucuso\\player_4\\"  # noqa: E501
        b"||AT||Lp!\\player_5\\Diejack1\\player_6\\Player1232\\player_7\\Mojojojo\\player_8\\DrLemonn\\player_9\\elmatap\\score_0\\4\\eof\\",  # noqa: E501
        b"\\statusresponse\\1\\score_1\\2\\score_2\\1\\score_3\\10\\score_4\\14\\score_5\\-3\\score_6\\11\\score_7\\25\\score_8\\18\\score_9\\5\\"  # noqa: E501
        b"ping_0\\67\\ping_1\\184\\ping_2\\265\\ping_3\\255\\ping_4\\54\\ping_5\\218\\ping_6\\208\\ping_7\\136\\ping_8\\70\\ping_9\\64\\team_0\\0"  # noqa: E501
        b"\\team_1\\0\\team_2\\1\\team_3\\0\\team_4\\1\\team_5\\0\\team_6\\1\\team_7\\1\\team_8\\0\\team_9\\0\\kills_0\\4\\kills_1\\2\\kills_2\\1"  # noqa: E501
        b"\\kills_3\\5\\kills_4\\14\\kills_5\\3\\kills_6\\6\\kills_7\\10\\kills_8\\8\\kills_9\\6\\tkills_5\\2\\tkills_9\\2\\deaths_0\\6\\deaths_1\\9"  # noqa: E501
        b"\\deaths_2\\4\\deaths_3\\4\\deaths_4\\8\\deaths_5\\4\\deaths_6\\7\\eof\\",
        b"\\statusresponse\\2\\deaths_7\\5\\deaths_8\\7\\deaths_9\\4"
        b"\\arrests_3\\1\\arrests_6\\1\\arrests_7\\3\\arrests_8\\2\\arrests_9"
        b"\\1\\arrested_1\\1\\arrested_2\\2\\arrested_4\\1\\arrested_5\\1\\arrested_6\\1"
        b"\\arrested_9\\2\\queryid\\AMv1\\final\\\\eof\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["hostname"] == (
        "[C=FF0000][c=33CCCC]>|S[C=FFFFFF]S|<[c=ffff00]Arg[C=ffffff]"
        "en[c=33CCCC]tina®[c=ff0000]-By FNXgaming.com"
    )
    assert data["hostport"] == "10780"
    assert data["queryid"] == "AMv1"
    assert data["final"] == ""
    assert "statusresponse" not in data
    assert "eof" not in data
    assert data["players"][3]["player"] == "«|FAL|cucuso"
    assert data["players"][4]["kills"] == "14"
    assert data["players"][5]["kills"] == "3"
    assert data["players"][8]["arrests"] == "2"
    assert data["players"][0]["ping"] == "67"
    assert data["players"][2]["score"] == "1"


@pytest.mark.django_db()
def test_gs1_serverquery_is_supported(udp_server):
    payload = [
        b"\\player_3\\Morgan\\score_3\\6\\ping_3\\53\\team_3\\1\\kills_3\\6\\deaths_3\\7"
        b"\\arrested_3\\1\\player_4\\Jericho\\score_4\\3\\ping_4\\46\\team_4\\0\\kills_4\\3"
        b"\\deaths_4\\12\\player_5\\Bolint\\score_5\\21\\ping_5\\57\\team_5\\1\\kills_5\\16"
        b"\\deaths_5\\8\\arrests_5\\1\\player_6\\FsB\\score_6\\2\\ping_6\\46\\team_6\\1\\kills_6\\5"
        b"\\deaths_6\\10\\tkills_6\\1\\arrested_6\\1\\player_7\\t00naab\\score_7\\11\\ping_7\\27"
        b"\\team_7\\0\\kills_7\\11\\vip_7\\1\\player_8\\ob\\score_8\\2\\ping_8\\74\\team_8\\1"
        b"\\kills_8\\2\\deaths_8\\3\\player_9\\martino\\score_9\\5\\ping_9\\67\\team_9\\1\\queryid\\2",
        b"\\hostname\\-==MYT Team Svr==-\\numplayers\\13\\maxplayers\\16"
        b"\\gametype\\VIP Escort\\gamevariant\\SWAT 4\\mapname\\Fairfax Residence"
        b"\\hostport\\10480\\password\\false\\gamever\\1.1\\round\\5\\numrounds\\5"
        b"\\timeleft\\286\\timespecial\\0\\swatscore\\41\\suspectsscore\\36\\swatwon"
        b"\\1\\suspectswon\\2\\player_0\\ugatz\\score_0\\0\\ping_0\\43\\team_0\\1"
        b"\\deaths_0\\9\\player_1\\|CSI|Miami\\score_1\\8\\ping_1\\104\\team_1\\0"
        b"\\kills_1\\8\\deaths_1\\4\\player_2\\aphawil\\score_2\\7\\ping_2\\69"
        b"\\team_2\\0\\kills_2\\8\\deaths_2\\11\\tkills_2\\2\\arrests_2\\1\\queryid\\1",
        b"\\kills_9\\5\\deaths_9\\2\\player_10\\conoeMadre\\score_10\\7\\ping_10\\135\\team_10\\0"
        b"\\kills_10\\7\\deaths_10\\2\\player_11\\Enigma51\\score_11\\0\\ping_11\\289\\team_11\\0"
        b"\\deaths_11\\1\\player_12\\Billy\\score_12\\0\\ping_12\\999\\team_12\\0\\queryid\\3\\final\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["hostname"] == "-==MYT Team Svr==-"
    assert data["numplayers"] == "13"
    assert data["suspectsscore"] == "36"
    assert data["timeleft"] == "286"
    assert data["final"] == ""
    assert data["players"][12]["score"] == "0"
    assert data["players"][3]["player"] == "Morgan"
    assert data["players"][12]["ping"] == "999"


@pytest.mark.django_db()
def test_original_swat_protocol_is_supported(udp_server):
    payload = [
        b"\\hostname\\[C=FFFF00]WWW.HOUSEOFPAiN.TK (Antics)\\numplayers\\4"
        b"\\maxplayers\\12\\gametype\\Barricaded Suspects\\gamevariant\\SWAT 4"
        b"\\mapname\\The Wolcott Projects\\hostport\\10480\\password\\0\\gamever\\1.0"
        b"\\player_0\\Navis\\player_1\\TAMAL(SPEC)\\player_2\\Player\\player_3\\Osanda(VIEW)"
        b"\\score_0\\15\\score_1\\0\\score_2\\3\\score_3\\0\\ping_0\\56\\ping_1\\160"
        b"\\ping_2\\256\\ping_3\\262\\final\\\\queryid\\1.1"
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["hostname"] == "[C=FFFF00]WWW.HOUSEOFPAiN.TK (Antics)"
    assert data["numplayers"] == "4"
    assert data["queryid"] == "1.1"
    assert data["final"] == ""
    assert len(data["players"]) == 4
    assert data["players"][0]["player"] == "Navis"
    assert data["players"][3]["ping"] == "262"


def test_response_incomplete(udp_server):
    payload = [
        b"\\hostname\\test\\queryid\\1",
        b"\\hostport\\10480\\queryid\\2",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert isinstance(data, asyncio.TimeoutError)


def test_response_malformed(udp_server):
    payload = [
        b"\\hostname\\test\\hostport\\10480\\final\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert isinstance(data, ResponseMalformedError)


def test_vanilla_queryid_is_not_integer(udp_server):
    payload = [
        b"\\hostname\\test\\hostport\\10480\\queryid\\gs1\\final\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["queryid"] == "gs1"
    assert data["final"] == ""


def test_queryid_is_not_zero_based(udp_server):
    payload = [
        b"\\hostname\\test\\queryid\\1",
        b"\\hostport\\10480\\queryid\\2\\final\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["final"] == ""


def test_statusresponse_is_zero_based(udp_server):
    payload = [
        b"\\statusresponse\\0\\hostname\\test\\queryid\\AMv1\\eof\\",
        b"\\statusresponse\\1\\queryid\\AMv1\\final\\\\eof\\",
    ]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert data["final"] == ""
    assert "eof" not in data


def test_statusresponse_eof_removed_from_response_final_queryid_are_not(udp_server):
    payload = [b"\\statusresponse\\0\\hostname\\test\\queryid\\AMv1\\final\\\\eof\\"]
    udp_server.responses.extend(payload)
    data = query_servers(udp_server.server_address).pop()

    assert "statusresponse" not in data
    assert "eof" not in data
    assert data["queryid"] == "AMv1"
    assert data["final"] == ""
