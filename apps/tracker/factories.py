import json
import random
from collections import OrderedDict
from hashlib import md5
from ipaddress import IPv4Network
from urllib.parse import urlencode

from django.db.models.signals import post_save
import factory.fuzzy
from django.utils.encoding import force_bytes
from django.utils import timezone
from django_redis import get_redis_connection

from apps.tracker.entities import Team
from apps.tracker.models import (Server, Loadout, Game, Player, Alias,
                                 Profile, PlayerStats, Map, GametypeStats, Weapon,
                                 ServerStats, MapStats)
from apps.tracker.schema import (weapon_encoded, equipment_encoded, objectives_encoded,
                                 procedures_encoded, objective_status_encoded, ammo_encoded, mapnames_encoded,
                                 teams_reversed, coop_status_encoded, coop_status_reversed, weapon_reversed)
from apps.utils.misc import dumps, timestamp
from apps.geoip.factories import ISPFactory


class PlayerQueryResponse(dict):

    def to_items(self):
        items = []
        player_id = self.pop('id')
        for key, value in self.items():
            items.append('%s_%s' % (key, player_id))
            items.append(value)
        return items


class ServerQueryResponse(dict):

    def to_items(self):
        items = []
        for key, value in self.items():
            if key in ('players', 'objectives'):
                for sub_item in value:
                    items.extend(sub_item.to_items())
            else:
                items.extend((key, value))
        return items

    def as_gamespy(self):
        items = self.to_items() + ['queryid', '1', 'final']
        return b'\\' + b'\\'.join(map(force_bytes, items)) + b'\\'


class PlayerQueryFactory(factory.Factory):
    id = factory.Sequence(lambda n: str(n))
    player = factory.Faker('first_name')
    ping = factory.fuzzy.FuzzyInteger(25, 9999)
    score = factory.fuzzy.FuzzyInteger(10, 30)
    kills = factory.fuzzy.FuzzyInteger(0, 1)
    vip = 0

    class Meta:
        model = PlayerQueryResponse


class ServerQueryFactory(factory.Factory):
    hostname = 'Swat4 Server'
    hostport = 10480
    password = 0
    gamevariant = 'SWAT 4'
    gamever = '1.1'
    gametype = 'VIP Escort'
    mapname = 'A-Bomb Nightclub'
    numplayers = 0
    maxplayers = 16
    round = 4
    numrounds = 5
    swatscore = 100
    suspectsscore = 0
    players = []
    objectives = []

    class Meta:
        model = ServerQueryResponse

    @factory.post_generation
    def with_players_count(obj, create, extracted, **kwargs):
        if extracted:
            obj['players'] = PlayerQueryFactory.create_batch(extracted)


class PlayerStatusFactory(factory.DictFactory):
    id = factory.Sequence(lambda n: str(n))
    name = factory.Faker('first_name')
    ping = factory.fuzzy.FuzzyInteger(25, 9999)
    score = factory.fuzzy.FuzzyInteger(5, 50)
    team = factory.fuzzy.FuzzyChoice([Team.swat, Team.suspects])
    vip = False
    kills = factory.fuzzy.FuzzyInteger(1, 10)


class ServerStatusFactory(factory.DictFactory):
    hostname = 'Swat4 Server'
    hostport = 10480
    password = 0
    statsenabled = 0
    gamevariant = 'SWAT 4'
    gamever = '1.1'
    gametype = 'VIP Escort'
    mapname = 'A-Bomb Nightclub'
    numplayers = 0
    maxplayers = 16
    round = 4
    numrounds = 5
    timeleft = 100
    timespecial = 0
    swatscore = 10
    suspectsscore = 10
    swatwon = 1
    suspectswon = 2
    bombsdefused = 0
    bombstotal = 0
    tocreports = 0
    weaponssecured = 0
    players = []
    objectives = []


@factory.django.mute_signals(post_save)
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

    @factory.post_generation
    def status(obj, create, extracted, **kwargs):
        if extracted:
            redis = get_redis_connection()
            redis.hset('servers', obj.address, dumps(extracted))


class ListedServerFactory(ServerFactory):
    listed = True


class LoadoutFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Loadout
        django_get_or_create = ('primary', 'secondary',
                                'primary_ammo', 'secondary_ammo',
                                'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five',
                                'head', 'body', 'breacher')

    primary = 'None'
    primary_ammo = 'None'
    secondary = 'None'
    secondary_ammo = 'None'
    equip_one = 'None'
    equip_two = 'None'
    equip_three = 'None'
    equip_four = 'None'
    equip_five = 'None'
    breacher = 'None'
    head = 'None'
    body = 'None'


class RandomLoadoutFactory(LoadoutFactory):
    primary = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    primary_ammo = factory.fuzzy.FuzzyChoice(ammo_encoded.values())
    secondary = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    secondary_ammo = factory.fuzzy.FuzzyChoice(ammo_encoded.values())
    equip_one = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_two = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_three = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_four = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_five = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    breacher = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    head = factory.fuzzy.FuzzyChoice(equipment_encoded.values())
    body = factory.fuzzy.FuzzyChoice(equipment_encoded.values())


class MapFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyChoice(choices=list(mapnames_encoded.values()))

    class Meta:
        django_get_or_create = ('name',)
        model = Map


class GameFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Game

    mapname = 1
    gametype = 'VIP Escort'
    outcome = 'swat_vip_escape'
    map = factory.SubFactory(MapFactory)
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

    name = factory.Faker('word')
    profile = factory.SubFactory(ProfileFactory)
    isp = factory.SubFactory(ISPFactory)


class PlayerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Player

    game = factory.SubFactory(GameFactory)
    alias = factory.SubFactory(AliasFactory)
    loadout = factory.SubFactory(LoadoutFactory)
    ip = factory.Faker('ipv4_public')
    vip = False
    admin = factory.Faker('pybool')
    dropped = factory.Faker('pybool')
    team = factory.fuzzy.FuzzyChoice(teams_reversed.keys())
    team_legacy = factory.LazyAttribute(lambda o: teams_reversed[o.team])

    class Params:
        common = factory.Trait(
            score=factory.Faker('pyint', min_value=-100, max_value=100),
            time=factory.Faker('pyint', min_value=0, max_value=1000),
            kills=factory.Faker('pyint', min_value=0, max_value=100),
            teamkills=factory.Faker('pyint', min_value=0, max_value=10),
            deaths=factory.Faker('pyint', min_value=0, max_value=30),
            suicides=factory.LazyAttribute(lambda o: o.deaths - random.randint(0, o.deaths)),
            arrests=factory.Faker('pyint', min_value=0, max_value=30),
            arrested=factory.Faker('pyint', min_value=0, max_value=30),
            kill_streak=factory.LazyAttribute(lambda o: random.randint(int(bool(o.kills)), o.kills)),
            arrest_streak=factory.LazyAttribute(lambda o: random.randint(int(bool(o.arrests)), o.arrests)),
            death_streak=factory.LazyAttribute(lambda o: random.randint(int(bool(o.deaths)), o.deaths)),
        )
        coop = factory.Trait(
            common=True,
            coop_status=factory.fuzzy.FuzzyChoice(list(coop_status_encoded.values())[1:]),
            coop_status_legacy=factory.LazyAttribute(lambda o: coop_status_reversed[o.coop_status]),
            coop_hostage_arrests=factory.Faker('pyint', min_value=0, max_value=30),
            coop_hostage_hits=factory.Faker('pyint', min_value=0, max_value=30),
            coop_hostage_incaps=factory.Faker('pyint', min_value=0, max_value=30),
            coop_hostage_kills=factory.Faker('pyint', min_value=0, max_value=30),
            coop_enemy_arrests=factory.Faker('pyint', min_value=0, max_value=30),
            coop_enemy_incaps=factory.Faker('pyint', min_value=0, max_value=30),
            coop_enemy_kills=factory.Faker('pyint', min_value=0, max_value=30),
            coop_enemy_incaps_invalid=factory.Faker('pyint', min_value=0, max_value=30),
            coop_enemy_kills_invalid=factory.Faker('pyint', min_value=0, max_value=30),
            coop_toc_reports=factory.Faker('pyint', min_value=0, max_value=100),
        )
        ve = factory.Trait(
            common=True,
            vip_captures=factory.Faker('pyint', min_value=0, max_value=3),
            vip_rescues=factory.Faker('pyint', min_value=0, max_value=3),
            vip_escapes=factory.LazyAttribute(lambda o: int(o.vip)),
            vip_kills_valid=factory.Faker('pyint', min_value=0, max_value=1),
            vip_kills_invalid=factory.Faker('pyint', min_value=0, max_value=1),
        )
        sg = factory.Trait(
            common=True,
            sg_escapes=factory.Faker('pyint', min_value=0, max_value=1),
            sg_kills=factory.Faker('pyint', min_value=0, max_value=10),
        )
        rd = factory.Trait(
            common=True,
            rd_bombs_defused=factory.Faker('pyint', min_value=0, max_value=5),
        )


class WeaponFactory(factory.django.DjangoModelFactory):
    player = factory.SubFactory(PlayerFactory)
    name = factory.fuzzy.FuzzyChoice(weapon_reversed.keys())
    name_legacy = factory.LazyAttribute(lambda o: weapon_reversed[o.name])

    time = factory.Faker('pyint', min_value=1, max_value=300)
    shots = factory.Faker('pyint', min_value=0, max_value=100)
    hits = factory.Faker('pyint', min_value=0, max_value=300)
    teamhits = factory.Faker('pyint', min_value=0, max_value=100)
    kills = factory.Faker('pyint', min_value=0, max_value=50)
    teamkills = factory.Faker('pyint', min_value=0, max_value=10)

    class Meta:
        model = Weapon


class AbstractStatsFactory(factory.django.DjangoModelFactory):
    category = factory.fuzzy.FuzzyChoice(['score', 'kills', 'deaths', 'teamkills', 'suicides'])
    profile = factory.SubFactory(ProfileFactory)
    year = factory.LazyAttribute(lambda o: timezone.now().year)
    points = factory.fuzzy.FuzzyFloat(-1000, 1000)
    position = None


class PlayerStatsFactory(AbstractStatsFactory):
    category_legacy = factory.LazyAttribute(lambda o: getattr(PlayerStats.LegacyCategory, o.category))

    class Meta:
        model = PlayerStats


class ServerStatsFactory(AbstractStatsFactory):
    server = factory.SubFactory(ServerFactory)

    class Meta:
        model = ServerStats


class MapStatsFactory(AbstractStatsFactory):
    map = factory.SubFactory(MapFactory)

    class Meta:
        model = MapStats


class GametypeStatsFactory(AbstractStatsFactory):
    gametype = 'VIP Escort'

    class Meta:
        model = GametypeStats


class BaseGameData(dict):
    mapping = {}

    @classmethod
    def encode_value(cls, item):
        if isinstance(item, list):
            return [cls.encode_value(sub_item) for sub_item in item]
        elif isinstance(item, BaseGameData):
            return item.to_encoded()
        else:
            return item

    def to_encoded(self):
        result = {}
        for name, value in self.items():
            result[self.mapping[name]] = self.encode_value(value)
        return result

    def to_json(self):
        return json.dumps(self.to_encoded())

    def to_julia_dict(self):
        def add_items(result_dict, keys, value):
            if isinstance(value, dict):
                for dict_key, dict_value in value.items():
                    add_items(result_dict, keys + (dict_key,), dict_value)
            elif isinstance(value, list):
                for list_idx, list_item in enumerate(value):
                    add_items(result_dict, keys + (list_idx,), list_item)
            else:
                result_dict[keys] = value
        # turn lists into enumerated dicts
        result = {}
        add_items(result, (), self.to_encoded())
        return result

    def to_julia_v1(self):
        """Convert dict data to julia v1 php's $_POST array like querystring"""
        return urlencode(OrderedDict([
            (str(keys[0]) + ''.join('[%s]' % array_idx for array_idx in keys[1:]), value)
            for keys, value in sorted(self.to_julia_dict().items())
        ]))

    def to_julia_v2(self):
        """Convert dict data to julia v2 dot delimited querytring"""
        return urlencode(OrderedDict([
            ('.'.join(map(str, keys)), value)
            for keys, value in sorted(self.to_julia_dict().items())
        ]))


class LoadoutGameData(BaseGameData):
    mapping = {
        'primary': 0,
        'primary_ammo': 1,
        'secondary': 2,
        'secondary_ammo': 3,
        'equip_one': 4,
        'equip_two': 5,
        'equip_three': 6,
        'equip_four': 7,
        'equip_five': 8,
        'breacher': 9,
        'body': 10,
        'head': 11,
    }


class WeaponGameData(BaseGameData):
    mapping = {
        'name': 0,
        'time': 1,
        'shots': 2,
        'hits': 3,
        'teamhits': 4,
        'kills': 5,
        'teamkills': 6,
        'distance': 7
    }


class PlayerGameData(BaseGameData):
    mapping = {
        'id': 0,
        'ip': 1,
        'dropped': 2,
        'admin': 3,
        'vip': 4,
        'name': 5,
        'team': 6,
        'time': 7,
        'score': 8,
        'kills': 9,
        'teamkills': 10,
        'deaths': 11,
        'suicides': 12,
        'arrests': 13,
        'arrested': 14,
        'kill_streak': 15,
        'arrest_streak': 16,
        'death_streak': 17,
        'vip_captures': 18,
        'vip_rescues': 19,
        'vip_escapes': 20,
        'vip_kills_valid': 21,
        'vip_kills_invalid': 22,
        'rd_bombs_defused': 23,
        'rd_crybaby': 24,
        'sg_kills': 25,
        'sg_escapes': 26,
        'sg_crybaby': 27,
        'coop_hostage_arrests': 28,
        'coop_hostage_hits': 29,
        'coop_hostage_incaps': 30,
        'coop_hostage_kills': 31,
        'coop_enemy_arrests': 32,
        'coop_enemy_incaps': 33,
        'coop_enemy_kills': 34,
        'coop_enemy_incaps_invalid': 35,
        'coop_enemy_kills_invalid': 36,
        'coop_toc_reports': 37,
        'coop_status': 38,
        'loadout': 39,
        'weapons': 40,
    }


class ObjectiveGameData(BaseGameData):
    mapping = {
        'name': 0,
        'status': 1
    }


class ProcedureGameData(BaseGameData):
    mapping = {
        'name': 0,
        'status': 1,
        'score': 2
    }


class ServerGameData(BaseGameData):
    mapping = {
        'tag': 0,
        'version': 1,
        'port': 2,
        'timestamp': 3,
        'hash': 4,
        'gamename': 5,
        'gamever': 6,
        'hostname': 7,
        'gametype': 8,
        'mapname': 9,
        'passworded': 10,
        'player_num': 11,
        'player_max': 12,
        'round_num': 13,
        'round_max': 14,
        'time_absolute': 15,
        'time': 16,
        'time_limit': 17,
        'vict_swat': 18,
        'vict_sus': 19,
        'score_swat': 20,
        'score_sus': 21,
        'outcome': 22,
        'bombs_defused': 23,
        'bombs_total': 24,
        'coop_objectives': 25,
        'coop_procedures': 26,
        'players': 27,
        'extra_key': 99999,
    }


class LoadoutGameDataFactory(factory.Factory):
    primary = factory.fuzzy.FuzzyChoice(equipment_encoded)
    secondary = factory.fuzzy.FuzzyChoice(equipment_encoded)
    equip_one = factory.fuzzy.FuzzyChoice(equipment_encoded)
    equip_two = factory.fuzzy.FuzzyChoice(equipment_encoded)
    equip_three = factory.fuzzy.FuzzyChoice(equipment_encoded)
    equip_four = factory.fuzzy.FuzzyChoice(equipment_encoded)
    equip_five = factory.fuzzy.FuzzyChoice(equipment_encoded)
    breacher = factory.fuzzy.FuzzyChoice(equipment_encoded)
    head = factory.fuzzy.FuzzyChoice(equipment_encoded)
    body = factory.fuzzy.FuzzyChoice(equipment_encoded)

    class Meta:
        model = LoadoutGameData


class WeaponGameDataFactory(factory.Factory):
    name = factory.fuzzy.FuzzyChoice(weapon_encoded)
    time = factory.fuzzy.FuzzyInteger(60, 300)
    shots = factory.fuzzy.FuzzyInteger(100, 200)
    hits = factory.fuzzy.FuzzyInteger(50, 100)
    teamhits = factory.fuzzy.FuzzyInteger(5, 15)
    kills = factory.fuzzy.FuzzyInteger(1, 10)
    distance = factory.fuzzy.FuzzyInteger(100, 2000)

    class Meta:
        model = WeaponGameData


class SimplePlayerGameDataFactory(factory.Factory):
    id = factory.Sequence(lambda n: str(n))
    name = factory.Faker('first_name')
    dropped = 0
    vip = 0
    time = factory.fuzzy.FuzzyInteger(1, 900)
    score = factory.fuzzy.FuzzyInteger(10, 30)
    kills = factory.fuzzy.FuzzyInteger(0, 1)
    deaths = factory.fuzzy.FuzzyInteger(1, 15)
    suicides = 0
    teamkills = factory.fuzzy.FuzzyInteger(0, 2)
    arrests = factory.fuzzy.FuzzyInteger(0, 1)
    arrested = factory.fuzzy.FuzzyInteger(0, 1)
    kill_streak = factory.fuzzy.FuzzyInteger(0, 8)
    arrest_streak = factory.fuzzy.FuzzyInteger(1, 3)
    death_streak = factory.fuzzy.FuzzyInteger(2, 9)
    coop_status = 2

    @factory.post_generation
    def ip(obj, create, extracted, **kwargs):
        if extracted:
            obj['ip'] = extracted
        elif create:
            obj['ip'] = str(IPv4Network('127.0.0.0/24')[random.randint(1, 254)])

    class Meta:
        model = PlayerGameData


class PlayerGameDataFactory(SimplePlayerGameDataFactory):

    @factory.post_generation
    def loadout(obj, create, extracted, **kwargs):
        if extracted is not None:
            obj['loadout'] = extracted
        elif create:
            obj['loadout'] = LoadoutGameDataFactory(**kwargs)

    @factory.post_generation
    def weapons(obj, create, extracted, **kwargs):
        if extracted:
            obj['weapons'] = extracted
        elif create:
            obj['weapons'] = WeaponGameDataFactory.create_batch(random.randint(1, 5), **kwargs)


class ObjectiveGameDataFactory(factory.Factory):
    name = factory.fuzzy.FuzzyChoice(objectives_encoded)
    status = factory.fuzzy.FuzzyChoice(objective_status_encoded)

    class Meta:
        model = ObjectiveGameData


class ProcedureGameDataFactory(factory.Factory):
    name = factory.fuzzy.FuzzyChoice(procedures_encoded)
    status = factory.LazyAttribute(lambda obj: '%s/%s' % (random.randint(1, 10),
                                                          random.randint(10, 15)))
    score = factory.fuzzy.FuzzyInteger(-5, 25)

    class Meta:
        model = ProcedureGameData


class ServerGameDataFactory(factory.Factory):
    tag = factory.fuzzy.FuzzyText(length=6)
    version = factory.fuzzy.FuzzyChoice(['1.0', '1.0.0', '1.0.1', '1.2.0'])
    port = factory.fuzzy.FuzzyInteger(1000, 30000)
    timestamp = factory.LazyAttribute(lambda o: int(timestamp()))
    gamever = '1.1'
    hostname = 'Swat4 Server'
    mapname = 4
    player_num = factory.fuzzy.FuzzyInteger(0, 16)
    player_max = 16
    round_num = 1
    round_max = 5
    time_absolute = 1500
    time = 850
    time_limit = 900
    vict_swat = 1
    vict_sus = 0
    score_swat = factory.fuzzy.FuzzyInteger(100, 150)
    score_sus = factory.fuzzy.FuzzyInteger(70, 90)
    outcome = 0

    @factory.post_generation
    def hash(obj, create, extracted, **kwargs):
        if create:
            key = kwargs.get('hash__key') or 'key'
            hash = md5(b''.join(map(force_bytes, [key, obj['port'], obj['timestamp']])))
            obj['hash'] = hash.hexdigest()[-8:]

    @factory.post_generation
    def with_players_count(obj, create, extracted, **kwargs):
        if extracted:
            obj['players'] = PlayerGameDataFactory.create_batch(extracted, **kwargs)

    @factory.post_generation
    def with_objectives_count(obj, create, extracted, **kwargs):
        if extracted:
            obj['coop_objectives'] = ObjectiveGameDataFactory.create_batch(extracted, **kwargs)

    @factory.post_generation
    def with_procedures_count(obj, create, extracted, **kwargs):
        if extracted:
            obj['coop_procedures'] = ProcedureGameDataFactory.create_batch(extracted, **kwargs)

    class Meta:
        model = ServerGameData
