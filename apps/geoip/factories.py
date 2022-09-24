import random
from ipaddress import IPv4Network, IPv4Address

import factory
import factory.fuzzy

from apps.geoip.models import IP, ISP


class ISPFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ISP
        django_get_or_create = ('name', 'country')

    name = factory.Faker('word')
    country = None

    @factory.post_generation
    def ip(obj, create, extracted, **kwargs):

        if kwargs:
            extracted = [kwargs]

        if not extracted:
            return

        if not isinstance(extracted, (tuple, list)):
            extracted = [extracted]

        for item in extracted:
            ip_from = ip_to = None

            if item in (1, True):
                ip_from, ip_to = '127.0.0.0', '127.0.0.255'
            elif isinstance(item, dict):
                ip_from, ip_to = item['from'], item['to']
            elif item:
                ip_addr = IPv4Network(item)
                ip_from, ip_to = ip_addr[0], ip_addr[-1]

            if ip_from and ip_to:
                ip = IPFactory(isp=obj,
                               range_from=int(IPv4Address(ip_from)),
                               range_to=int(IPv4Address(ip_to)))
                obj.ip_set.add(ip)


class IPFactory(factory.django.DjangoModelFactory):
    isp = factory.SubFactory(ISPFactory)
    range_from = factory.LazyAttribute(lambda o: int(IPv4Address('127.0.0.1')))
    range_to = factory.LazyAttribute(lambda o: int(IPv4Address('127.0.0.1') + random.randint(1, 65534)))

    class Meta:
        model = IP
        django_get_or_create = ('range_from', 'range_to')
