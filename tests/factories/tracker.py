import random

import factory
from django.db.models.signals import post_save
from django_redis import get_redis_connection
from factory import fuzzy

from apps.tracker.models import (
    Alias,
    Game,
    Map,
    Player,
    Profile,
    Server,
    Weapon,
)
from apps.tracker.schema import (
    coop_status_encoded,
    coop_status_reversed,
    mapnames_encoded,
    teams_reversed,
    weapon_reversed,
)
from apps.tracker.utils.misc import force_clean_name
from apps.utils.misc import dumps

from .geoip import ISPFactory
from .loadout import LoadoutFactory


@factory.django.mute_signals(post_save)
class ServerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Server
        django_get_or_create = ("ip", "port")

    ip = "127.0.0.100"
    port = factory.LazyAttribute(lambda o: random.randint(10000, 65535))
    hostname = "Swat4 Server"
    hostname_clean = factory.LazyAttribute(
        lambda o: force_clean_name(o.hostname) if o.hostname else None
    )
    enabled = True

    @factory.post_generation
    def country(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            obj.country = extracted

        ISPFactory.create(country=extracted, ip__from=obj.ip, ip__to=obj.ip)

    @factory.post_generation
    def status(obj, create, extracted, **kwargs):
        if extracted:
            redis = get_redis_connection()
            redis.hset("servers", obj.address, dumps(extracted))


class ListedServerFactory(ServerFactory):
    listed = True


class MapFactory(factory.django.DjangoModelFactory):
    name = fuzzy.FuzzyChoice(choices=list(mapnames_encoded.values()))

    class Meta:
        django_get_or_create = ("name",)
        model = Map


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game

    mapname = 1
    gametype = "VIP Escort"
    gametype_legacy = 1
    outcome = "swat_vip_escape"
    map = factory.SubFactory(MapFactory)
    server = factory.SubFactory(ServerFactory)
    player_num = 16

    @factory.post_generation
    def players(obj, created, extracted, **kwargs):
        if not created:
            return
        if kwargs.get("batch"):
            batch = kwargs.pop("batch")
            PlayerFactory.create_batch(batch, game=obj, **kwargs)
        elif extracted:
            for player_kwargs in extracted:
                PlayerFactory(game=obj, **player_kwargs)


class ProfileFactory(factory.django.DjangoModelFactory):
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

    @factory.post_generation
    def first_seen_at(obj, create, extracted, **kwargs):
        if extracted:
            obj.first_seen_at = extracted
        elif obj.game_first:
            obj.first_seen_at = obj.game_first.date_finished

    @factory.post_generation
    def last_seen_at(obj, create, extracted, **kwargs):
        if extracted:
            obj.last_seen_at = extracted
        elif obj.game_last:
            obj.last_seen_at = obj.game_last.date_finished


class AliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Alias

    name = factory.Faker("word")
    profile = factory.SubFactory(ProfileFactory)
    isp = factory.SubFactory(ISPFactory)


class PlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Player

    game = factory.SubFactory(GameFactory)
    alias = factory.SubFactory(AliasFactory)
    loadout = factory.SubFactory(LoadoutFactory)
    ip = factory.Faker("ipv4_public")
    vip = False
    admin = factory.Faker("pybool")
    dropped = factory.Faker("pybool")
    team = fuzzy.FuzzyChoice(teams_reversed.keys())
    team_legacy = factory.LazyAttribute(lambda o: teams_reversed[o.team])

    class Params:
        common = factory.Trait(
            score=factory.Faker("pyint", min_value=-100, max_value=100),
            time=factory.Faker("pyint", min_value=0, max_value=1000),
            kills=factory.Faker("pyint", min_value=0, max_value=100),
            teamkills=factory.Faker("pyint", min_value=0, max_value=10),
            deaths=factory.Faker("pyint", min_value=0, max_value=30),
            suicides=factory.LazyAttribute(lambda o: o.deaths - random.randint(0, o.deaths)),
            arrests=factory.Faker("pyint", min_value=0, max_value=30),
            arrested=factory.Faker("pyint", min_value=0, max_value=30),
            kill_streak=factory.LazyAttribute(
                lambda o: random.randint(int(bool(o.kills)), o.kills)
            ),
            arrest_streak=factory.LazyAttribute(
                lambda o: random.randint(int(bool(o.arrests)), o.arrests)
            ),
            death_streak=factory.LazyAttribute(
                lambda o: random.randint(int(bool(o.deaths)), o.deaths)
            ),
        )
        coop = factory.Trait(
            common=True,
            coop_status=fuzzy.FuzzyChoice(list(coop_status_encoded.values())[1:]),
            coop_status_legacy=factory.LazyAttribute(lambda o: coop_status_reversed[o.coop_status]),
            coop_hostage_arrests=factory.Faker("pyint", min_value=0, max_value=30),
            coop_hostage_hits=factory.Faker("pyint", min_value=0, max_value=30),
            coop_hostage_incaps=factory.Faker("pyint", min_value=0, max_value=30),
            coop_hostage_kills=factory.Faker("pyint", min_value=0, max_value=30),
            coop_enemy_arrests=factory.Faker("pyint", min_value=0, max_value=30),
            coop_enemy_incaps=factory.Faker("pyint", min_value=0, max_value=30),
            coop_enemy_kills=factory.Faker("pyint", min_value=0, max_value=30),
            coop_enemy_incaps_invalid=factory.Faker("pyint", min_value=0, max_value=30),
            coop_enemy_kills_invalid=factory.Faker("pyint", min_value=0, max_value=30),
            coop_toc_reports=factory.Faker("pyint", min_value=0, max_value=100),
        )
        ve = factory.Trait(
            common=True,
            vip_captures=factory.Faker("pyint", min_value=0, max_value=3),
            vip_rescues=factory.Faker("pyint", min_value=0, max_value=3),
            vip_escapes=factory.LazyAttribute(lambda o: int(o.vip)),
            vip_kills_valid=factory.Faker("pyint", min_value=0, max_value=1),
            vip_kills_invalid=factory.Faker("pyint", min_value=0, max_value=1),
        )
        sg = factory.Trait(
            common=True,
            sg_escapes=factory.Faker("pyint", min_value=0, max_value=1),
            sg_kills=factory.Faker("pyint", min_value=0, max_value=10),
        )
        rd = factory.Trait(
            common=True,
            rd_bombs_defused=factory.Faker("pyint", min_value=0, max_value=5),
        )


class WeaponFactory(factory.django.DjangoModelFactory):
    player = factory.SubFactory(PlayerFactory)
    name = fuzzy.FuzzyChoice(weapon_reversed.keys())
    name_legacy = factory.LazyAttribute(lambda o: weapon_reversed[o.name])

    time = factory.Faker("pyint", min_value=1, max_value=300)
    shots = factory.Faker("pyint", min_value=0, max_value=100)
    hits = factory.Faker("pyint", min_value=0, max_value=300)
    teamhits = factory.Faker("pyint", min_value=0, max_value=100)
    kills = factory.Faker("pyint", min_value=0, max_value=50)
    teamkills = factory.Faker("pyint", min_value=0, max_value=10)

    class Meta:
        model = Weapon
