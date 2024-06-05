import json
import random
from collections import OrderedDict
from hashlib import md5
from ipaddress import IPv4Network
from typing import ClassVar
from urllib.parse import urlencode

import factory
from django.utils.encoding import force_bytes
from factory import fuzzy

from apps.tracker.schema import (
    equipment_encoded,
    objective_status_encoded,
    objectives_encoded,
    procedures_encoded,
    weapon_encoded,
)
from apps.utils.misc import timestamp


class BaseGameData(dict):
    mapping: ClassVar[dict]

    @classmethod
    def encode_value(cls, item):
        match item:
            case list():
                return [cls.encode_value(sub_item) for sub_item in item]
            case BaseGameData():
                return item.to_encoded()
            case _:
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
                    add_items(
                        result_dict,
                        (
                            *keys,
                            dict_key,
                        ),
                        dict_value,
                    )
            elif isinstance(value, list):
                for list_idx, list_item in enumerate(value):
                    add_items(result_dict, (*keys, list_idx), list_item)
            else:
                result_dict[keys] = value

        # turn lists into enumerated dicts
        result = {}
        add_items(result, (), self.to_encoded())
        return result

    def to_julia_v1(self):
        """Convert dict data to julia v1 php's $_POST array like querystring"""
        return urlencode(
            OrderedDict(
                [
                    (str(keys[0]) + "".join(f"[{array_idx}]" for array_idx in keys[1:]), value)
                    for keys, value in sorted(self.to_julia_dict().items())
                ]
            )
        )

    def to_julia_v2(self):
        """Convert dict data to julia v2 dot delimited querytring"""
        return urlencode(
            OrderedDict(
                [
                    (".".join(map(str, keys)), value)
                    for keys, value in sorted(self.to_julia_dict().items())
                ]
            )
        )


class LoadoutGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "primary": 0,
        "primary_ammo": 1,
        "secondary": 2,
        "secondary_ammo": 3,
        "equip_one": 4,
        "equip_two": 5,
        "equip_three": 6,
        "equip_four": 7,
        "equip_five": 8,
        "breacher": 9,
        "body": 10,
        "head": 11,
    }


class WeaponGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "name": 0,
        "time": 1,
        "shots": 2,
        "hits": 3,
        "teamhits": 4,
        "kills": 5,
        "teamkills": 6,
        "distance": 7,
    }


class PlayerGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "id": 0,
        "ip": 1,
        "dropped": 2,
        "admin": 3,
        "vip": 4,
        "name": 5,
        "team": 6,
        "time": 7,
        "score": 8,
        "kills": 9,
        "teamkills": 10,
        "deaths": 11,
        "suicides": 12,
        "arrests": 13,
        "arrested": 14,
        "kill_streak": 15,
        "arrest_streak": 16,
        "death_streak": 17,
        "vip_captures": 18,
        "vip_rescues": 19,
        "vip_escapes": 20,
        "vip_kills_valid": 21,
        "vip_kills_invalid": 22,
        "rd_bombs_defused": 23,
        "rd_crybaby": 24,
        "sg_kills": 25,
        "sg_escapes": 26,
        "sg_crybaby": 27,
        "coop_hostage_arrests": 28,
        "coop_hostage_hits": 29,
        "coop_hostage_incaps": 30,
        "coop_hostage_kills": 31,
        "coop_enemy_arrests": 32,
        "coop_enemy_incaps": 33,
        "coop_enemy_kills": 34,
        "coop_enemy_incaps_invalid": 35,
        "coop_enemy_kills_invalid": 36,
        "coop_toc_reports": 37,
        "coop_status": 38,
        "loadout": 39,
        "weapons": 40,
    }


class ObjectiveGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "name": 0,
        "status": 1,
    }


class ProcedureGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "name": 0,
        "status": 1,
        "score": 2,
    }


class ServerGameData(BaseGameData):
    mapping: ClassVar[dict[str, int]] = {
        "tag": 0,
        "version": 1,
        "port": 2,
        "timestamp": 3,
        "hash": 4,
        "gamename": 5,
        "gamever": 6,
        "hostname": 7,
        "gametype": 8,
        "mapname": 9,
        "passworded": 10,
        "player_num": 11,
        "player_max": 12,
        "round_num": 13,
        "round_max": 14,
        "time_absolute": 15,
        "time": 16,
        "time_limit": 17,
        "vict_swat": 18,
        "vict_sus": 19,
        "score_swat": 20,
        "score_sus": 21,
        "outcome": 22,
        "bombs_defused": 23,
        "bombs_total": 24,
        "coop_objectives": 25,
        "coop_procedures": 26,
        "players": 27,
        "extra_key": 99999,
    }


class LoadoutGameDataFactory(factory.Factory):
    primary = fuzzy.FuzzyChoice(equipment_encoded)
    secondary = fuzzy.FuzzyChoice(equipment_encoded)
    equip_one = fuzzy.FuzzyChoice(equipment_encoded)
    equip_two = fuzzy.FuzzyChoice(equipment_encoded)
    equip_three = fuzzy.FuzzyChoice(equipment_encoded)
    equip_four = fuzzy.FuzzyChoice(equipment_encoded)
    equip_five = fuzzy.FuzzyChoice(equipment_encoded)
    breacher = fuzzy.FuzzyChoice(equipment_encoded)
    head = fuzzy.FuzzyChoice(equipment_encoded)
    body = fuzzy.FuzzyChoice(equipment_encoded)

    class Meta:
        model = LoadoutGameData


class WeaponGameDataFactory(factory.Factory):
    name = fuzzy.FuzzyChoice(weapon_encoded)
    time = fuzzy.FuzzyInteger(60, 300)
    shots = fuzzy.FuzzyInteger(100, 200)
    hits = fuzzy.FuzzyInteger(50, 100)
    teamhits = fuzzy.FuzzyInteger(5, 15)
    kills = fuzzy.FuzzyInteger(1, 10)
    distance = fuzzy.FuzzyInteger(100, 2000)

    class Meta:
        model = WeaponGameData


class SimplePlayerGameDataFactory(factory.Factory):
    id = factory.Sequence(lambda n: str(n))
    name = factory.Faker("first_name")
    dropped = 0
    vip = 0
    time = fuzzy.FuzzyInteger(1, 900)
    score = fuzzy.FuzzyInteger(10, 30)
    kills = fuzzy.FuzzyInteger(0, 1)
    deaths = fuzzy.FuzzyInteger(1, 15)
    suicides = 0
    teamkills = fuzzy.FuzzyInteger(0, 2)
    arrests = fuzzy.FuzzyInteger(0, 1)
    arrested = fuzzy.FuzzyInteger(0, 1)
    kill_streak = fuzzy.FuzzyInteger(0, 8)
    arrest_streak = fuzzy.FuzzyInteger(1, 3)
    death_streak = fuzzy.FuzzyInteger(2, 9)
    coop_status = 2

    @factory.post_generation
    def ip(obj, create, extracted, **kwargs):
        if extracted:
            obj["ip"] = extracted
        elif create:
            obj["ip"] = str(IPv4Network("127.0.0.0/24")[random.randint(1, 254)])

    class Meta:
        model = PlayerGameData


class PlayerGameDataFactory(SimplePlayerGameDataFactory):
    @factory.post_generation
    def loadout(obj, create, extracted, **kwargs):
        if extracted is not None:
            obj["loadout"] = extracted
        elif create:
            obj["loadout"] = LoadoutGameDataFactory(**kwargs)

    @factory.post_generation
    def weapons(obj, create, extracted, **kwargs):
        if extracted:
            obj["weapons"] = extracted
        elif create:
            obj["weapons"] = WeaponGameDataFactory.create_batch(random.randint(1, 5), **kwargs)


class ObjectiveGameDataFactory(factory.Factory):
    name = fuzzy.FuzzyChoice(objectives_encoded)
    status = fuzzy.FuzzyChoice(objective_status_encoded)

    class Meta:
        model = ObjectiveGameData


class ProcedureGameDataFactory(factory.Factory):
    name = fuzzy.FuzzyChoice(procedures_encoded)
    status = factory.LazyAttribute(lambda obj: f"{random.randint(1, 10)}/{random.randint(10, 15)}")
    score = fuzzy.FuzzyInteger(-5, 25)

    class Meta:
        model = ProcedureGameData


class ServerGameDataFactory(factory.Factory):
    tag = fuzzy.FuzzyText(length=6)
    version = fuzzy.FuzzyChoice(["1.0", "1.0.0", "1.0.1", "1.2.0"])
    port = fuzzy.FuzzyInteger(1000, 30000)
    timestamp = factory.LazyAttribute(lambda o: int(timestamp()))
    gamever = "1.1"
    hostname = "Swat4 Server"
    mapname = 4
    player_num = fuzzy.FuzzyInteger(0, 16)
    player_max = 16
    round_num = 1
    round_max = 5
    time_absolute = 1500
    time = 850
    time_limit = 900
    vict_swat = 1
    vict_sus = 0
    score_swat = fuzzy.FuzzyInteger(100, 150)
    score_sus = fuzzy.FuzzyInteger(70, 90)
    outcome = 0

    @factory.post_generation
    def hash(obj, create, extracted, **kwargs):
        if not create:
            return
        key = kwargs.get("hash__key") or "key"
        value = md5(b"".join(map(force_bytes, [key, obj["port"], obj["timestamp"]])))
        obj["hash"] = value.hexdigest()[-8:]

    @factory.post_generation
    def with_players_count(obj, create, extracted, **kwargs):
        if extracted:
            obj["players"] = PlayerGameDataFactory.create_batch(extracted, **kwargs)

    @factory.post_generation
    def with_objectives_count(obj, create, extracted, **kwargs):
        if extracted:
            obj["coop_objectives"] = ObjectiveGameDataFactory.create_batch(extracted, **kwargs)

    @factory.post_generation
    def with_procedures_count(obj, create, extracted, **kwargs):
        if extracted:
            obj["coop_procedures"] = ProcedureGameDataFactory.create_batch(extracted, **kwargs)

    class Meta:
        model = ServerGameData
