import pytest

from apps.tracker.entities import GameType
from apps.tracker.factories import (ServerFactory, ServerStatusFactory)


def test_get_server_detail_for_disabled_404(db, api_client):
    server = ServerFactory(enabled=False,
                           listed=True,
                           status=ServerStatusFactory())
    response = api_client.get(f'/api/servers/{server.pk}/')
    assert response.status_code == 404
    assert response.data == {'detail': 'Not found.'}


@pytest.mark.parametrize('address', ['62.210.142.5:10480', '999999999'])
def test_get_server_detail_not_found_404(db, api_client, address):
    response = api_client.get(f'/api/servers/{address}/')
    assert response.status_code == 404
    assert response.data == {'detail': 'Not found.'}


@pytest.mark.parametrize('address', ['foo', 'None', '1bar', ' '])
def test_get_server_detail_bad_address_404(db, api_client, address):
    response = api_client.get(f'/api/servers/{address}/')
    assert response.status_code == 404
    assert response.data == {'detail': 'Not found.'}


def test_get_server_detail_versus(db, api_client, django_assert_max_num_queries):
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

    with django_assert_max_num_queries(2):
        response = api_client.get(f'/api/servers/{server.pk}/')

    status = response.data['status']
    assert response.status_code == 200
    assert response.data['id'] == server.pk
    assert response.data['ip'] == server.ip
    assert response.data['port'] == server.port
    assert response.data['address'] == f'{server.ip}:{server.port}'
    assert response.data['country'] == 'UK'
    assert response.data['hostname'] == 'Swat4 Server'
    assert response.data['merged_into'] is None
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


def test_get_server_detail_coop(db, api_client, django_assert_max_num_queries):
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

    with django_assert_max_num_queries(2):
        response = api_client.get(f'/api/servers/{server.pk}/')

    status = response.data['status']
    assert response.status_code == 200
    assert response.data['id'] == server.pk
    assert response.data['ip'] == server.ip
    assert response.data['port'] == server.port
    assert response.data['address'] == f'{server.ip}:{server.port}'
    assert response.data['country'] == 'UK'
    assert response.data['hostname'] == 'Swat4 Server'
    assert response.data['merged_into'] is None
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


@pytest.mark.parametrize('is_listed', [True, False])
def test_get_server_with_no_status(db, api_client, django_assert_max_num_queries, is_listed):
    server = ServerFactory(
        enabled=True,
        listed=is_listed,
        country='UK',
        hostname='Swat4 Server',
        status=None,
    )

    with django_assert_max_num_queries(2):
        response = api_client.get(f'/api/servers/{server.pk}/')

    assert response.status_code == 200
    assert response.data['id'] == server.pk
    assert response.data['country'] == 'UK'
    assert response.data['address'] == f'{server.ip}:{server.port}'
    assert response.data['hostname'] == 'Swat4 Server'
    assert response.data['merged_into'] is None
    assert response.data['status'] is None


@pytest.mark.parametrize('with_main_status', [True, False])
@pytest.mark.parametrize('with_merged_status', [True, False])
@pytest.mark.parametrize('with_main_listed', [True, False])
@pytest.mark.parametrize('with_merged_listed', [True, False])
@pytest.mark.parametrize('with_main_enabled', [True, False])
@pytest.mark.parametrize('with_merged_enabled', [True, False])
def test_get_server_detail_for_merged(
    db,
    api_client,
    django_assert_max_num_queries,
    with_main_status,
    with_merged_status,
    with_main_listed,
    with_merged_listed,
    with_main_enabled,
    with_merged_enabled,
):
    server = ServerFactory(
        ip='2.2.2.2',
        port=10480,
        country='GB',
        enabled=with_main_enabled,
        listed=with_main_listed,
        status=ServerStatusFactory() if with_main_status else None,
    )
    ServerFactory(
        ip='1.1.1.1',
        port=15480,
        merged_into=server,
        enabled=with_merged_enabled,
        listed=with_merged_listed,
        status=ServerStatusFactory(
            hostname=r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]'
        ) if with_merged_status else None,
    )

    with django_assert_max_num_queries(2):
        response = api_client.get('/api/servers/1.1.1.1:15480/')

    assert response.status_code == 200
    assert response.data['merged_into'] == {
        'id': server.pk,
        'ip': '2.2.2.2',
        'port': 10480,
        'address': '2.2.2.2:10480',
        'country': 'GB',
        'country_human': 'United Kingdom',
        'hostname': 'Swat4 Server',
        'name_clean': 'Swat4 Server',
        'pinned': False,
    }

    if with_merged_status:
        assert response.data['status']['hostname'] == r'[c=FF00FF][b][u]Swat4[\u][C=0000FF]Server[\c]'
    else:
        assert response.data['status'] is None
