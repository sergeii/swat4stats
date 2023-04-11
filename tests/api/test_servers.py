import pytest

from apps.geoip.factories import ISPFactory
from apps.tracker.entities import GameType
from apps.tracker.factories import (ServerFactory, ServerStatusFactory,
                                    ServerQueryFactory, PlayerQueryFactory)
from apps.tracker.models import Server


def test_get_server_list(db, api_client):
    ServerFactory(listed=False)
    ServerFactory(listed=True)
    ServerFactory(enabled=False, listed=True, status=ServerStatusFactory())
    ServerFactory(listed=True, status=None)
    vip_server = ServerFactory(listed=True,
                               status=ServerStatusFactory(gametype='VIP Escort',
                                                          numplayers=16,
                                                          maxplayers=16))
    pinned_server = ServerFactory(listed=True,
                                  pinned=True,
                                  status=ServerStatusFactory(gametype='VIP Escort',
                                                             numplayers=16,
                                                             maxplayers=16))
    vip_server10 = ServerFactory(listed=True,
                                 status=ServerStatusFactory(gametype='VIP Escort',
                                                            numplayers=15,
                                                            maxplayers=18,
                                                            gamever='1.0'))
    bs_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='Barricaded Suspects'))
    coop_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='CO-OP'))
    sg_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='Smash And Grab',
                                                                      gamevariant='SWAT 4X',
                                                                      gamever='1.0'))
    tss_coop_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='CO-OP',
                                                                            gamevariant='SWAT 4X',
                                                                            gamever='1.0'))
    passworded_server = ServerFactory(listed=True,
                                      status=ServerStatusFactory(password=True))

    response = api_client.get('/api/servers/')
    listed_servers = [obj['id'] for obj in response.data]

    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert len(listed_servers) == 8
    assert listed_servers == [pinned_server.pk, vip_server.pk, vip_server10.pk,
                              bs_server.pk, coop_server.pk, sg_server.pk,
                              tss_coop_server.pk, passworded_server.pk]
    status = response.data[0]['status']
    assert status['hostname'] == 'Swat4 Server'
    assert status['gametype'] == 'VIP Escort'
    assert 'players' not in status
    assert 'time_round' not in status

    responses = [
        ({'empty': 'true'}, [bs_server.pk, coop_server.pk, sg_server.pk,
                             tss_coop_server.pk, passworded_server.pk]),
        ({'passworded': 'true'}, [passworded_server.pk]),
        ({'passworded': 'false'}, [pinned_server.pk, vip_server.pk, vip_server10.pk,
                                   bs_server.pk, coop_server.pk, sg_server.pk, tss_coop_server.pk]),
        ({'empty': 'false'}, [pinned_server.pk, vip_server.pk, vip_server10.pk]),
        ({'empty': 'false', 'full': 'false'}, [vip_server10.pk]),
        ({'empty': 'true', 'full': 'true'}, []),
        ({'empty': 'false', 'full': 'true'}, [pinned_server.pk, vip_server.pk]),
        ({'full': 'true', 'gametype': 'VIP Escort'}, [pinned_server.pk, vip_server.pk]),
        ({'full': 'true', 'gametype': 'CO-OP'}, []),
        ({'gametype': 'CO-OP'}, [coop_server.pk, tss_coop_server.pk]),
        ({'gamename': 'SWAT 4X'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamename': 'SWAT 4X', 'gametype': 'VIP Escort'}, []),
        ({'gamename': 'SWAT 4X', 'full': 'true'}, []),
        ({'gamename': 'SWAT 4X', 'full': 'False'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamever': '1.1'}, [pinned_server.pk, vip_server.pk,
                              bs_server.pk, coop_server.pk, passworded_server.pk]),
        ({'gamever': '1.0'}, [vip_server10.pk, sg_server.pk, tss_coop_server.pk]),
        ({'gamever': '1.1', 'gamename': 'SWAT 4X'}, []),
        ({'gamever': '1.1', 'gamename': 'SWAT 4'}, [pinned_server.pk, vip_server.pk,
                                                    bs_server.pk, coop_server.pk, passworded_server.pk]),
        ({'gamever': '1.0', 'gamename': 'SWAT 4'}, [vip_server10.pk]),
        ({'gamever': '1.0', 'gamename': 'SWAT 4', 'gametype': 'Smash And Grab'}, []),
        ({'gamever': '1.0', 'gamename': 'SWAT 4X'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamename': 'Invalid'}, []),
        ({'gametype': 'Unknown'}, []),
    ]

    for filters, expected_data in responses:
        response = api_client.get('/api/servers/', data=filters)
        assert [obj['id'] for obj in response.data] == expected_data, filters


@pytest.mark.parametrize('server_factory', [
    # disabled server
    lambda: ServerFactory(enabled=False, listed=True, status=ServerStatusFactory()),
    # unlisted_server
    lambda: ServerFactory(enabled=True, listed=False, status=ServerStatusFactory()),
    # server with no status
    lambda: ServerFactory(enabled=True, listed=True, status=None),
])
def test_get_server_detail_invalid_status_404(db, api_client, server_factory):
    server = server_factory()
    response = api_client.get(f'/api/servers/{server.pk}/')
    assert response.status_code == 404
    assert response.data == {'detail': 'Not found.'}


def test_get_server_detail_not_found_404(db, api_client):
    response = api_client.get('/api/servers/999999999/')
    assert response.status_code == 404
    assert response.data == {'detail': 'Not found.'}


def test_get_server_detail_versus(db, api_client):
    server = ServerFactory(
        enabled=True,
        listed=True,
        country='UK',
        hostname='Swat4 Server',
        status=ServerStatusFactory(
            hostname=r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]',
            gametype=GameType.vip_escort.value,
        ),
    )

    response = api_client.get(f'/api/servers/{server.pk}/')
    status = response.data['status']
    assert response.status_code == 200
    assert response.data['id'] == server.pk
    assert response.data['country'] == 'UK'
    assert response.data['hostname'] == 'Swat4 Server'
    assert status['hostname'] == r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]'
    assert status['hostname_clean'] == 'Swat4Server'
    assert status['hostname_html'] == ('<span style="color:#FF00FF;">Swat4</span>'
                                       '<span style="color:#0000FF;">Server</span>')
    assert status['gametype'] == 'VIP Escort'
    assert status['gamename'] == 'SWAT 4'
    assert status['time_round'] == 100
    assert status['rules'].startswith('One player on the SWAT team is randomly chosen to be the VIP.')
    assert status['briefing'] is None
    assert 'players' in status


def test_get_server_detail_coop(db, api_client):
    server = ServerFactory(
        enabled=True,
        listed=True,
        country='UK',
        hostname='Swat4 Server',
        status=ServerStatusFactory(
            hostname=r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]',
            gametype=GameType.co_op.value,
        ),
    )

    response = api_client.get(f'/api/servers/{server.pk}/')
    status = response.data['status']
    assert response.status_code == 200
    assert response.data['id'] == server.pk
    assert response.data['country'] == 'UK'
    assert response.data['hostname'] == 'Swat4 Server'
    assert status['hostname'] == r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]'
    assert status['hostname_clean'] == 'Swat4Server'
    assert status['hostname_html'] == ('<span style="color:#FF00FF;">Swat4</span>'
                                       '<span style="color:#0000FF;">Server</span>')
    assert status['gametype'] == 'CO-OP'
    assert status['gamename'] == 'SWAT 4'
    assert status['time_round'] == 100
    assert status['rules'].startswith('Play single player missions with a group of up to five officers.')
    assert status['briefing'].startswith('We\'re being called up for a rapid deployment')
    assert 'players' in status


def test_add_server_flow(db, api_client, udp_server):
    server_ip, server_port = udp_server.server_address
    ISPFactory(country='uk', ip=server_ip)
    udp_server.responses.append(ServerQueryFactory(hostname='Swat4 Server',
                                                   hostport=server_port - 1,
                                                   players=PlayerQueryFactory.create_batch(16)).as_gamespy())

    response = api_client.post('/api/servers/', data={'ip': server_ip, 'port': server_port-1})

    assert response.status_code == 201
    assert response.data['ip'] == server_ip
    assert response.data['port'] == server_port - 1
    assert response.data['hostname'] == 'Swat4 Server'
    assert response.data['country'] is None
    assert 'status' not in response

    server = Server.objects.get(ip=server_ip, port=server_port-1)
    assert server.status_port == server_port
    assert server.hostname == 'Swat4 Server'
    assert server.country == 'uk'
    assert server.listed
    assert server.enabled

    detail_response = api_client.get(f'/api/servers/{server.pk}/')
    status = detail_response.data['status']
    assert len(status['players']) == 16
    assert status['players'][0]['team'] in ['swat', 'suspects']
    assert len(status['objectives']) == 0


def test_add_server_not_available(db, api_client, udp_server):
    server_ip, query_port = udp_server.server_address
    join_port = query_port - 1
    udp_server.responses.append(b'')
    response = api_client.post('/api/servers/', data={'ip': server_ip, 'port': join_port})
    assert response.status_code == 400
    assert str(response.data['non_field_errors'][0]) == 'Ensure the server is running at port %s' % join_port
    assert not Server.objects.count()


def test_add_server_already_exists(db, api_client):
    ServerFactory(ip='127.0.0.1', port=10480, listed=True)
    response = api_client.post('/api/servers/', data={'ip': '127.0.0.1', 'port': 10480})
    assert response.status_code == 400
    assert str(response.data['non_field_errors'][0]) == 'The specified server already exists'
    assert Server.objects.filter(ip='127.0.0.1', port=10480).count() == 1


def test_add_server_existing_is_relisted(db, api_client, udp_server):
    udp_server.responses.append(ServerQueryFactory(hostname='Swat4 Server',
                                                   hostport=udp_server.address.port,
                                                   players=PlayerQueryFactory.create_batch(16)).as_gamespy())

    server = ServerFactory(ip=udp_server.address.ip,
                           port=udp_server.address.port,
                           hostname='Old Server Name',
                           listed=False,
                           failures=15)

    response = api_client.post('/api/servers/', data={'ip': udp_server.address.ip, 'port': udp_server.address.port})

    assert response.status_code == 201
    assert response.data['hostname'] == 'Swat4 Server'

    server.refresh_from_db()

    assert server.listed
    assert server.failures == 0


def test_add_server_unavailable_is_not_relisted(db, api_client, udp_server):
    udp_server.responses.append(b'')

    server = ServerFactory(ip=udp_server.address.ip,
                           port=udp_server.address.port,
                           hostname='Old Server Name',
                           listed=False,
                           failures=15)

    response = api_client.post('/api/servers/', data={'ip': udp_server.address.ip, 'port': udp_server.address.port})

    assert response.status_code == 400

    server.refresh_from_db()

    assert not server.listed
    assert server.failures == 15


def test_get_server_by_ip(db, api_client):
    disabled_server = ServerFactory(enabled=False, listed=True, status=ServerStatusFactory())
    unlisted_server = ServerFactory(enabled=True, listed=False, status=ServerStatusFactory())
    no_status_server = ServerFactory(enabled=True, listed=True, status=None)
    ok_server = ServerFactory(enabled=True,
                              listed=True,
                              country='UK',
                              hostname='Old Server Name',
                              status=ServerStatusFactory(hostname=r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]'))

    response = api_client.get('/api/servers/62.210.142.5:10480/')
    assert response.status_code == 404

    response = api_client.get(f'/api/servers/{disabled_server.ip}:{disabled_server.port}/')
    assert response.status_code == 404

    response = api_client.get(f'/api/servers/{unlisted_server.ip}:{unlisted_server.port}/')
    assert response.status_code == 404

    response = api_client.get(f'/api/servers/{no_status_server.ip}:{no_status_server.port}/')
    assert response.status_code == 404

    response = api_client.get(f'/api/servers/{ok_server.ip}:{ok_server.port}/')
    assert response.status_code == 200
    assert response.data['id'] == ok_server.pk
    assert response.data['status']
