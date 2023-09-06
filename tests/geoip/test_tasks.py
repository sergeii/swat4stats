from datetime import datetime, timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from pytz import UTC

from apps.geoip.models import IP, ISP
from apps.geoip.tasks import delete_expired_ips
from apps.utils.test import freeze_timezone_now
from tests.factories.geoip import IPFactory, ISPFactory


def test_expired_ips_are_deleted(db):
    now = datetime(2016, 5, 1, 23, 0, 0, tzinfo=UTC)

    with freeze_timezone_now(now - timedelta(days=360)):
        ip1 = IPFactory()
    with freeze_timezone_now(now - timedelta(days=181)):
        ip2 = IPFactory()
    with freeze_timezone_now(now - timedelta(days=180)):
        ip3 = IPFactory()
    with freeze_timezone_now(now - timedelta(days=1)):
        ip4 = IPFactory()
    with freeze_timezone_now(now + timedelta(days=1)):
        ip5 = IPFactory()

    assert IP.objects.count() == 5

    with freeze_timezone_now(now):
        delete_expired_ips.delay()

    assert IP.objects.get(pk=ip3.pk)
    assert IP.objects.get(pk=ip4.pk)
    assert IP.objects.get(pk=ip5.pk)

    assert IP.objects.count() == 3
    assert IP.objects.filter(pk__in=[ip1.pk, ip2.pk]).count() == 0


def test_ips_are_deleted_whois_returns_fresh_data(db, whois_mock):
    now = timezone.now()

    with freeze_timezone_now(now - timedelta(days=360)):
        isp1 = ISPFactory(name="foo", ip="1.2.0.0/16")
        expired_ip = isp1.ip_set.get()

    with freeze_timezone_now(now):
        isp2 = ISPFactory(name="bar", ip="4.3.0.0/16")
        fresh_ip = isp2.ip_set.get()

    assert IP.objects.expired().get() == expired_ip

    obj, created = ISP.objects.match_or_create("1.2.3.4")
    assert obj == isp1

    obj, created = ISP.objects.match_or_create("4.3.2.1")
    assert obj == isp2

    assert len(whois_mock.mock_calls) == 0

    with freeze_timezone_now(now):
        delete_expired_ips.delay()

    with pytest.raises(ObjectDoesNotExist):
        IP.objects.get(pk=expired_ip.pk)
    assert IP.objects.get(pk=fresh_ip.pk)

    whois_mock.return_value = {"nets": [{"description": "bar", "cidr": "1.2.0.0/16"}]}

    obj, created = ISP.objects.match_or_create("1.2.3.4")
    assert obj == isp2
    assert not created
