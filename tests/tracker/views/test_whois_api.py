import pytest

from apps.geoip.factories import ISPFactory
from apps.tracker.factories import ServerFactory, GameFactory, PlayerFactory, ProfileFactory
from apps.tracker.utils import force_clean_name


@pytest.fixture(autouse=True)
def test_server(db):
    return ServerFactory(ip='127.11.12.44', port=10480, listed=True)


@pytest.fixture(autouse=True)
def test_game(db, test_server):
    return GameFactory(server=test_server)


@pytest.fixture(autouse=True)
def _test_isp(db):
    ISPFactory(ip='88.44.88.0/24', country='GB', name='Sky')
    ISPFactory(ip='1.1.0.0/16', country='US', name='Comcast')
    ISPFactory(ip='1.0.0.0/8', country='CA', name='Virgin')


def assert_success_code(response):
    assert response.content.decode()[0] == '0'


def assert_error_code(response):
    assert response.content.decode()[0] == '1'


@pytest.mark.parametrize('request_qs, ok', [
    ('0=foo&1=whois&2=ham&3=Serge%09127.0.0.1', True),
    ('0=foo&1=whois&2=ham&3=Serge%09127.0.0.1&4=admin&5=1.1.1.1', True),
    ('0=foo&1=whois&2=%21&3=Serge%09127.0.0.1&4=&5=', True),
    ('0=spam&1=whois&2=ham&3=Serge2%091.1.10.20', True),
    ('', False),  # empty qs
    ('0=foo', False),  # only hash is present
    ('0=foo&1=whois', False),
    ('0=foo&1=whois&3=baz', False),
    ('0=foo&1=invalid&2=ham&3=baz', False),  # invalid command name
    ('0=foo&1=whois&2=ham&3=baz&spam=eggs', False),  # extra param
    ('0=spam&1=whois&2=ham&3=eggs', False),  # invalid arg
    ('0=spam&1=whois&2=ham&3=Serge2%09127.0.0.299', False),  # invalid ip
])
def test_valid_data_passed_to_whois_api_is_validated(client, request_qs, ok):
    response = client.get(f'/api/whois/?{request_qs}', HTTP_X_REAL_IP='127.11.12.44')
    assert response.status_code == 200
    assert response.content
    if ok:
        assert_success_code(response)
    else:
        assert_error_code(response)


def test_unregistered_server_is_not_permitted_to_use_whois_api(client):
    response = client.get('/api/whois/?0=foo&1=whois&2=ham&3=Serge%091.1.10.20', HTTP_X_REAL_IP='192.168.1.125')
    assert_error_code(response)


def test_unlisted_server_is_not_permitted_to_use_whois_api(client):
    ServerFactory(ip='127.0.0.5', port=10480, listed=False)
    response = client.get('/api/whois/?0=foo&1=whois&2=ham&3=Serge%091.1.10.20', HTTP_X_REAL_IP='127.0.0.5')
    assert_error_code(response)


@pytest.mark.parametrize('name, ip, country, isp', [
    ('Killa', '88.44.88.16', 'United Kingdom', 'Sky'),
    ('Cop', '1.1.102.18', 'United States of America', 'Comcast'),
    ('Butcher', '1.2.19.18', 'United States of America', 'Test ISP'),
])
def test_whois_match_country_isp(client, whois_mock, name, ip, country, isp):
    response = client.get(f'/api/whois/?0=foo&1=whois&2=ham&3={name}%09{ip}', HTTP_X_REAL_IP='127.11.12.44')
    assert_success_code(response)
    messages = [force_clean_name(line) for line in response.content.decode().splitlines()[2:]]
    assert len(messages) == 1
    assert messages[0] == f'{ip} belongs to {country} ({isp})'


@pytest.mark.parametrize('name, ip, country, isp', [
    ('Butcher', '1.2.19.18', 'Canada', 'Virgin'),
    ('Killa', '8.1.9.18', 'Terra Incognita', 'Unknown ISP'),
])
def test_whois_dont_match_country_isp(client, whois_mock, name, ip, country, isp):
    whois_mock.side_effect = ValueError('whois data contains no nets')
    response = client.get(f'/api/whois/?0=foo&1=whois&2=ham&3={name}%09{ip}', HTTP_X_REAL_IP='127.11.12.44')
    assert_success_code(response)
    messages = [force_clean_name(line) for line in response.content.decode().splitlines()[2:]]
    assert len(messages) == 1
    assert messages[0] == f'{ip} belongs to {country} ({isp})'


@pytest.mark.parametrize('name, ip, alias, server', [
    ('Butcher', '4.8.4.8', 'Butcher', 'Awesome Server'),
    ('Butcher', '4.8.4.40', 'Butcher', 'Awesome Server'),
    ('Killa', '4.8.4.40', 'Butcher', 'Awesome Server'),
    ('Player', '4.8.4.99', 'Player', None),
])
def test_whois_match_profile(client, whois_mock, name, ip, alias, server):
    isp = ISPFactory(ip='4.8.4.0/24', country='CY', name='Epic')
    profile = ProfileFactory(name='Butcher', game_last__server__hostname='Awesome Server')
    PlayerFactory(alias__name='Butcher', alias__isp=isp, alias__profile=profile, ip='4.8.4.40')
    response = client.get(f'/api/whois/?0=foo&1=whois&2=ham&3={name}%09{ip}', HTTP_X_REAL_IP='127.11.12.44')
    assert_success_code(response)

    messages = [line for line in response.content.decode().split('\n')[2:]]
    assert messages[0].startswith(f'[c=00FF00][b]{ip}[\\b][\\c] belongs to [c=00FF00]Cyprus[\\c] (Epic)')

    has_server = server is not None
    has_alias = alias != name

    if not has_alias:
        assert len(messages) == 1 + has_server
    else:
        assert len(messages) == 2 + has_server
        assert messages[1] == f'[c=00FF00][b]{name}[\\b][\\c] is better known as [c=00FF00][b]{alias}[\\b][\\c]'

    if has_server:
        assert messages[-1] == f'[c=00FF00][b]{alias}[\\b][\\c] was last seen on [c=00FF00]{server}[\\c] now'
