from apps.geoip.factories import ISPFactory
from apps.tracker.factories import ServerFactory, ServerQueryFactory, PlayerQueryFactory
from apps.tracker.models import Server


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
