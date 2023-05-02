import socket
from ipaddress import IPv4Address

import pytest

from apps.geoip.factories import ISPFactory
from apps.geoip.models import IP, ISP


@pytest.fixture(autouse=True)
def _setup_fixture(db):
    pass


def test_match_existing_ip_range(whois_mock):
    whois_mock.return_value = {'nets': [{'country': 'UN',
                                         'description': 'foo',
                                         'cidr': '1.2.3.0/24'}]}
    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj1.name == 'foo'
    assert obj1.country == 'un'
    assert obj1.ip_set.count() == 1
    assert len(whois_mock.mock_calls) == 1

    whois_mock.return_value = {'nets': [{'country': 'EU',
                                         'description': 'bar',
                                         'cidr': '1.2.3.0/24'}]}
    obj2, created = ISP.objects.match_or_create('1.2.3.5')
    assert not created
    assert obj2.name == 'foo'
    assert obj2.country == 'un'
    assert obj2.ip_set.count() == 1
    assert len(whois_mock.mock_calls) == 1

    assert obj1 == obj2
    the_ip = IP.objects.get()
    assert the_ip.range_from_normal == '1.2.3.0'
    assert the_ip.range_to_normal == '1.2.3.255'

    whois_mock.return_value = {'nets': [{'country': 'UN',
                                         'description': 'foo',
                                         'cidr': '1.0.0.0/8'}]}
    obj3, created = ISP.objects.match_or_create('1.0.0.1')
    assert obj3.pk == obj1.pk

    assert len(whois_mock.mock_calls) == 2
    assert obj1.ip_set.count() == 2
    assert ISP.objects.get() == obj1


@pytest.mark.parametrize('side_effect', [socket.timeout, TypeError, ValueError, UnicodeDecodeError])
def test_exceptions_raised_by_whois_are_ignored(side_effect, whois_mock):
    whois_mock.side_effect = side_effect
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj is None
    assert ISP.objects.count() == 0
    assert IP.objects.count() == 0


@pytest.mark.parametrize('whois_result', [
    {},
    {'nets': []},
    {'nets': [{'country': 'UN', 'description': 'foo'}]},
    {'nets': [{'country': 'UN', 'description': 'foo', 'cidr': None}]},
    {'nets': [{'country': 'UN', 'description': 'foo', 'cidr': '1.2.3.4/0'}]},
    {'nets': [{'country': 'UN', 'description': 'foo', 'cidr': '1.2.3.5/32, 1.2.3.6/32'}]},
])
def test_invalid_results_returned_by_whois_are_ignored(whois_result, whois_mock):
    whois_mock.return_value = whois_result
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj is None
    assert ISP.objects.count() == 0
    assert IP.objects.count() == 0


@pytest.mark.parametrize('whois_result', [
    {'nets': [{'foo': 'bar', 'cidr': '1.0.0.0/8'}]},
    {'nets': [{'country': None, 'description': None, 'cidr': '1.2.0.0/16'}]},
    {'nets': [{'country': 'un', 'description': None, 'cidr': '1.2.3.0/24'}]},
    {'nets': [{'country': 'un', 'description': 'localhost', 'cidr': '1.2.3.0/26'}]},
    {'nets': [{'country': 'un', 'description': 'localhost', 'cidr': '1.2.3.4/32'}]},
    {'nets': [{'country': 'UN', 'description': 'foo', 'cidr': '1.2.3.4'}]},
    {'nets': [{'country': 'UN', 'description': 'foo', 'cidr': '1.2.3.5/32, 1.2.3.0/24'}]},
])
def test_valid_whois_results(whois_result, whois_mock):
    whois_mock.return_value = whois_result
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.ip_set.get()


def test_null_country_and_orgname_are_accepted(whois_mock):
    whois_mock.return_value = {'nets': [{'cidr': '1.2.0.0/16'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.name is None
    assert obj.country is None
    ip_obj = obj.ip_set.get()
    assert ip_obj.range_from_normal == '1.2.0.0'
    assert ip_obj.range_to_normal == '1.2.255.255'


def test_null_country_is_accepted(whois_mock):
    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.2.0.0/16'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.name == 'foo'
    assert obj.country is None
    assert obj.ip_set.count() == 1


def test_null_orgname_is_accepted(whois_mock):
    whois_mock.return_value = {'nets': [{'country': 'UN', 'cidr': '1.2.0.0/16'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.name is None
    assert obj.country == 'un'
    assert obj.ip_set.count() == 1


def test_query_same_org_name(whois_mock):
    whois_mock.return_value = {'nets': [{'country': 'un', 'description': 'foo', 'cidr': '1.2.0.0/16'}]}
    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created

    whois_mock.return_value = {'nets': [{'country': 'un', 'description': 'foo', 'cidr': '4.3.2.0/24'}]}
    obj2, created = ISP.objects.match_or_create('4.3.2.1')
    assert not created

    assert obj1.pk == obj2.pk
    assert obj1.name == 'foo'
    assert obj1.ip_set.count() == 2
    assert ISP.objects.count() == 1
    assert IP.objects.count() == 2


def test_query_same_org_name_different_country(whois_mock):
    whois_mock.return_value = {'nets': [{'country': 'un', 'description': 'foo', 'cidr': '1.2.0.0/16'}]}
    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created

    whois_mock.return_value = {'nets': [{'country': 'eu', 'description': 'foo', 'cidr': '4.3.2.0/24'}]}
    obj2, created = ISP.objects.match_or_create('4.3.2.1')
    assert created

    assert obj1.pk != obj2.pk
    assert obj1.name == 'foo'
    assert obj2.name == 'foo'
    assert obj1.country == 'un'
    assert obj2.country == 'eu'
    assert obj1.ip_set.count() == 1
    assert obj2.ip_set.count() == 1


def test_empty_orgname_is_different_from_another_empty_orgname(whois_mock):
    whois_mock.return_value = {'nets': [{'country': 'un', 'description': None, 'cidr': '1.2.0.0/16'}]}
    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj1.name is None
    assert obj1.country == 'un'

    whois_mock.return_value = {'nets': [{'country': 'un', 'description': None, 'cidr': '4.3.2.0/24'}]}
    obj2, created = ISP.objects.match_or_create('4.3.2.1')
    assert created
    assert obj2.name is None
    assert obj2.country == 'un'

    assert obj1.pk != obj2.pk
    assert obj1.ip_set.count() == 1
    assert obj2.ip_set.count() == 1
    assert ISP.objects.count() == 2
    assert IP.objects.count() == 2


def test_query_empty_country_with_nonempty_orgname(whois_mock):
    whois_mock.return_value = {'nets': [{'country': None, 'description': 'foo', 'cidr': '1.2.0.0/16'}]}
    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj1.name == 'foo'
    assert obj1.country is None

    whois_mock.return_value = {'nets': [{'country': None, 'description': 'foo', 'cidr': '4.3.2.0/24'}]}
    obj2, created = ISP.objects.match_or_create('4.3.2.1')
    assert not created
    assert obj2.name == 'foo'
    assert obj2.country is None

    assert obj1.pk == obj2.pk
    assert obj1.ip_set.count() == 2
    assert ISP.objects.count() == 1


def test_matching_range_from_known_ip_range_skips_whois_lookup_even_null_isp_name(whois_mock):
    whois_mock.return_value = {'nets': [{'cidr': '1.2.0.0/16'}]}

    obj1, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj1.name is None
    assert obj1.country is None
    assert obj1.ip_set.count() == 1
    assert len(whois_mock.mock_calls) == 1

    obj2, created = ISP.objects.match_or_create('1.2.3.5')
    assert not created
    assert obj2.name is None
    assert obj2.country is None
    assert obj2.ip_set.count() == 1
    assert len(whois_mock.mock_calls) == 1

    assert obj1.pk == obj2.pk


@pytest.mark.parametrize('net_description, isp_name', [
    ('foo', 'foo'),
    (' foo', 'foo'),
    ('foo\nbar', 'foo'),
    (' foo\nbar', 'foo'),
    ('\nfoo\nbar', 'foo'),
    ('\n\nfoo\nbar', 'foo'),
    ('\n foo\nbar', 'foo'),
    ('\n \nfoo\n\nbar', 'foo'),
    ('foo\rbar', 'foo'),
    (' foo\rbar', 'foo'),
    ('\rfoo\rbar', 'foo'),
    ('\r\rfoo\rbar', 'foo'),
    ('\r foo\rbar', 'foo'),
    ('\r \nfoo\r\rbar', 'foo'),
    ('Mobile Services\n'
     'Infra-aw\n'
     '********************************************\n'
     'In case of improper use originating from our\n'
     'network, please mail Tele2 Security at\n'
     '<abuse@tele2.com>\n'
     '********************************************',
     'Mobile Services'),
])
def test_multiline_description_is_handled(whois_mock, net_description, isp_name):
    whois_mock.return_value = {
        'nets': [{'country': 'eu', 'description': net_description, 'cidr': '1.2.0.0/16'}]
    }
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.name == isp_name
    assert obj.country == 'eu'
    assert obj.ip_set.count() == 1


@pytest.mark.parametrize('net_description, isp_name', [
    ('foo', 'foo'),
    ('foo' * 1000, ('foo' * 1000)[:255]),
])
def test_long_description_is_truncated(whois_mock, net_description, isp_name):
    whois_mock.return_value = {
        'nets': [{'country': 'eu', 'description': net_description, 'cidr': '1.2.0.0/16'}]
    }
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.name == isp_name
    assert obj.country == 'eu'
    assert obj.ip_set.count() == 1


def test_invalid_ip_ranges_from_whois_result_are_ignored(whois_mock):
    invalid_ranges = [
        'foo',
        '0.0.0.0/122',
    ]
    for invalid_range in invalid_ranges:
        whois_mock.return_value = {'nets': {'cidr': invalid_range}}
        obj, created = ISP.objects.match_or_create('1.2.3.4')
        assert obj is None
        assert not created

    assert IP.objects.count() == 0
    assert ISP.objects.count() == 0
    assert len(whois_mock.mock_calls) == len(invalid_ranges)


def test_match_will_prefer_the_smallest_ip_range(whois_mock):
    ISPFactory(name='foo', ip__from='127.0.0.0', ip__to='127.255.255.255')
    ISPFactory(name='bar', ip__from='127.0.0.0', ip__to='127.0.255.255')
    ISPFactory(name='baz', ip__from='127.0.0.0', ip__to='127.0.0.255')
    ISPFactory(name='ham', ip__from='127.0.0.0', ip__to='127.0.0.1')
    ISPFactory(name='spam', ip__from='127.0.0.1', ip__to='127.0.0.1')

    assert ISP.objects.match('127.0.0.1')[0].name == 'spam'
    assert ISP.objects.match('127.0.0.2')[0].name == 'baz'
    assert ISP.objects.match('127.0.0.0')[0].name == 'ham'
    assert ISP.objects.match('127.0.244.15')[0].name == 'bar'
    assert ISP.objects.match('127.12.244.15')[0].name == 'foo'
    assert ISP.objects.match('127.255.255.255')[0].name == 'foo'

    assert not whois_mock.called


def test_whois_ip_range_is_validated(whois_mock):
    whois_mock.return_value = {'nets': [{'cidr': '1.2.0.0/16'}]}
    obj, created = ISP.objects.match_or_create('4.3.2.1')

    assert IP.objects.count() == 0
    assert ISP.objects.count() == 0
    assert obj is None
    assert not created
    assert len(whois_mock.mock_calls) == 1

    whois_mock.return_value = {'nets': [{'cidr': '11.22.33.0/24'}]}
    obj, created = ISP.objects.match_or_create('11.22.34.2')

    assert IP.objects.count() == 0
    assert ISP.objects.count() == 0
    assert obj is None
    assert not created
    assert len(whois_mock.mock_calls) == 2


def test_match_or_create_will_not_add_same_ip_range(whois_mock):
    isp = ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')
    whois_mock.return_value = {'nets': [{'cidr': '1.0.0.0/8'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert obj == isp
    assert obj.name == 'foo'
    assert not created
    assert obj.ip_set.count() == 1
    assert IP.objects.count() == 1
    assert len(whois_mock.mock_calls) == 1


def test_too_large_ip_range_leads_to_whois_call(whois_mock):
    isp = ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')
    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.0.0.0/8'}]}

    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj == isp
    # the returned ip range is same
    assert IP.objects.count() == 1
    assert len(whois_mock.mock_calls) == 1

    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.2.3.0/24'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj == isp
    # the returned ip range is different
    assert IP.objects.count() == 2
    assert len(whois_mock.mock_calls) == 2

    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj == isp
    assert len(whois_mock.mock_calls) == 2

    obj, created = ISP.objects.match_or_create('1.2.3.5')
    assert not created
    assert obj == isp
    assert len(whois_mock.mock_calls) == 2


def test_extra_whois_query_returns_existing_range(whois_mock):
    # too large ip range, extra whois call is required
    isp1 = ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')  # noqa
    isp2 = ISPFactory(name='bar', ip__from='1.0.0.0', ip__to='1.127.255.255')
    isp3 = ISPFactory(name='baz', ip__from='1.2.3.0', ip__to='1.2.3.255')

    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.2.3.0/24'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert obj == isp3
    assert len(whois_mock.mock_calls) == 0

    # although an extra whois call was performed, the resolved ip range had already existed
    # and it had been assigned to a different isp
    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.0.0.0/9'}]}
    obj, created = ISP.objects.match_or_create('1.2.4.1')
    assert not created
    assert obj == isp2
    assert len(whois_mock.mock_calls) == 1
    assert ISP.objects.count() == 3
    assert IP.objects.count() == 3
    assert set(ISP.objects.values_list('name', flat=True)) == {'foo', 'bar', 'baz'}


def test_extra_whois_query_fails_fallback_to_matched_isp(whois_mock):
    whois_mock.side_effect = socket.timeout
    isp = ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert obj == isp
    assert not created
    assert len(whois_mock.mock_calls) == 1
    assert ISP.objects.count() == 1
    assert IP.objects.count() == 1


def test_extra_whois_request_returns_another_isp(whois_mock):
    isp = ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')

    whois_mock.return_value = {'nets': [{'description': 'bar', 'cidr': '1.2.3.0/24'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert created
    assert obj.pk != isp.pk
    assert obj.name == 'bar'
    assert len(whois_mock.mock_calls) == 1
    assert ISP.objects.count() == 2
    assert IP.objects.count() == 2
    whois_mock.reset_mock()

    obj, created = ISP.objects.match_or_create('1.2.3.100')
    assert not created
    assert obj.name == 'bar'
    assert len(whois_mock.mock_calls) == 0
    assert ISP.objects.count() == 2
    assert IP.objects.count() == 2


def test_no_extra_whois_request_is_required_for_accepted_length(whois_mock):
    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.2.3.0/24'}]}
    # too large ip range, extra whois call is required
    ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')

    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert len(whois_mock.mock_calls) == 1
    whois_mock.reset_mock()

    obj, created = ISP.objects.match_or_create('1.2.3.5')
    assert not created
    assert obj.name == 'foo'
    assert len(whois_mock.mock_calls) == 0

    obj, created = ISP.objects.match_or_create('1.2.3.128')
    assert not created
    assert len(whois_mock.mock_calls) == 0

    assert IP.objects.count() == 2


def test_extra_whois_call_returns_same_ip_range(whois_mock):
    # range is too large
    ISPFactory(name='foo', ip__from='1.0.0.0', ip__to='1.255.255.255')
    # ip range is too large
    whois_mock.return_value = {'nets': [{'description': 'foo', 'cidr': '1.0.0.0/8'}]}
    obj, created = ISP.objects.match_or_create('1.2.3.4')
    assert not created
    assert len(whois_mock.mock_calls) == 1
    whois_mock.reset_mock()

    # same ip range, but different orgname
    obj, created = ISP.objects.match_or_create('1.2.3.5')
    assert not created
    assert obj.name == 'foo'

    assert ISP.objects.count() == 1
    assert IP.objects.count() == 1
    assert len(whois_mock.mock_calls) == 1


@pytest.mark.parametrize('ip,isp_name', [
    ('0.0.0.0', 'This Network'),
    ('127.0.0.1', 'Loopback'),
    ('192.0.0.1', 'IETF Protocol Assignments'),
    ('192.0.2.123', 'TEST-NET-1'),
    ('192.88.99.1', '6to4 Relay Anycast'),
    ('192.88.99.1', '6to4 Relay Anycast'),
    ('198.18.100.12', 'Network Interconnect Device Benchmark Testing'),
    ('198.51.100.100', 'TEST-NET-2'),
    ('203.0.113.3', 'TEST-NET-3'),
    ('224.0.0.1', 'Multicast'),
    ('255.255.255.255', 'Limited Broadcast'),
    ('192.168.1.100', 'Private-Use Networks'),
    ('10.212.10.100', 'Private-Use Networks'),
])
def test_whois_lookup_private_ip(ip, isp_name, whois_mock):
    isp, created = ISP.objects.match_or_create(ip)
    assert created
    assert isp.name == isp_name
    assert isp.country is None
    assert not whois_mock.called

    ip_obj = isp.ip_set.get()
    assert ip_obj.range_from == int(IPv4Address(ip))
    assert ip_obj.range_to == int(IPv4Address(ip))
