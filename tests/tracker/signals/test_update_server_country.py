import factory
import pytest
from django.db.models.signals import post_save

from apps.geoip.factories import ISPFactory
from apps.tracker.models import Server


@pytest.fixture
def isp(db):
    ISPFactory(country='cy', ip='43.12.98.0/24')


def test_country_is_updated_for_new_instances(isp):
    server = Server.objects.create_server('43.12.98.128', 10480)
    updated_server = Server.objects.get(pk=server.pk)
    assert updated_server.country == 'cy'


def test_country_is_updated_when_ip_is_changed(isp):
    with factory.django.mute_signals(post_save):
        server = Server.objects.create_server('12.12.31.13', 10480, country='my')
    created_server = Server.objects.get(pk=server.pk)
    assert created_server.country == 'my'
    server.ip = '43.12.98.14'
    server.save()
    updated_server = Server.objects.get(pk=server.pk)
    assert updated_server.country == 'cy'


def test_country_is_updated_when_country_is_emptied(isp):
    with factory.django.mute_signals(post_save):
        server = Server.objects.create_server('43.12.98.1', 10480, country='my')
    created_server = Server.objects.get(pk=server.pk)
    assert created_server.country == 'my'
    server.country = None
    server.save()
    updated_server = Server.objects.get(pk=server.pk)
    assert updated_server.country == 'cy'
