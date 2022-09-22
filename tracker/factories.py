import random
from ipaddress import IPv4Network, IPv4Address

import factory.fuzzy

from tracker.models import Server, Loadout, Game, Player, Alias, Profile, Weapon, ISP, IP


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


class ServerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Server
        django_get_or_create = ('ip', 'port')

    ip = '127.0.0.100'
    port = factory.LazyAttribute(lambda o: random.randint(10000, 65535))
    hostname = 'Swat4 Server'
    enabled = True

    @factory.post_generation
    def country(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            obj.country = extracted

        ISPFactory.create(country=extracted, ip__from=obj.ip, ip__to=obj.ip)


class LoadoutFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Loadout
        django_get_or_create = ('primary', 'secondary',
                                'primary_ammo', 'secondary_ammo',
                                'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five',
                                'head', 'body', 'breacher')

    primary = 0
    primary_ammo = 0
    secondary = 0
    secondary_ammo = 0
    equip_one = 0
    equip_two = 0
    equip_three = 0
    equip_four = 0
    equip_five = 0
    breacher = 0
    head = 0
    body = 0


class GameFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Game

    gametype = 1
    outcome = 6
    mapname = 11
    server = factory.SubFactory(ServerFactory)
    player_num = 16

    @factory.post_generation
    def players(obj, created, extracted, **kwargs):
        if not created:
            return
        if kwargs.get('batch'):
            batch = kwargs.pop('batch')
            PlayerFactory.create_batch(batch, game=obj, **kwargs)
        elif extracted:
            for player_kwargs in extracted:
                PlayerFactory(game=obj, **player_kwargs)


class ProfileFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('name')
    team = factory.LazyAttribute(lambda o: random.randint(0, 1))
    loadout = factory.SubFactory(LoadoutFactory)

    class Meta:
        model = Profile

    @factory.post_generation
    def game_first(obj, create, extracted, **kwargs):
        if extracted:
            obj.game_first = extracted
        elif kwargs:
            obj.game_first = GameFactory(**kwargs)

    @factory.post_generation
    def game_last(obj, create, extracted, **kwargs):
        if extracted:
            obj.game_last = extracted
        elif kwargs:
            obj.game_last = GameFactory(**kwargs)


class AliasFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Alias

    name = factory.Faker('word')
    profile = factory.SubFactory(ProfileFactory)
    isp = factory.SubFactory(ISPFactory)


class PlayerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Player

    game = factory.SubFactory(GameFactory)
    alias = factory.SubFactory(AliasFactory)
    loadout = factory.SubFactory(LoadoutFactory)
    ip = '127.0.0.1'
    vip = False
    admin = True
    team = 1


class WeaponFactory(factory.django.DjangoModelFactory):
    player = factory.SubFactory(PlayerFactory)
    name = 10

    class Meta:
        model = Weapon
