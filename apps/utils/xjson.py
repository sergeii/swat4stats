import json
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from dateutil.parser import parse as parse_date
from django.core.serializers.base import DeserializedObject
from django_redis.serializers.base import BaseSerializer


class XJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        match obj:
            case datetime():
                return OrderedDict(
                    [
                        ("__type__", "__datetime__"),
                        ("isoformat", obj.isoformat()),
                    ]
                )
            case date():
                return OrderedDict(
                    [
                        ("__type__", "__date__"),
                        ("isoformat", obj.isoformat()),
                    ]
                )
            case Decimal():
                return OrderedDict(
                    [
                        ("__type__", "__decimal__"),
                        ("decimal", str(obj)),
                    ]
                )
            case UUID():
                return OrderedDict(
                    [
                        ("__type__", "__uuid__"),
                        ("uuid", str(obj)),
                    ]
                )
            case DeserializedObject():
                return self.default(obj.object)
            case _:
                return super().default(obj)


def xjson_decoder(obj: dict) -> dict | datetime | date | Decimal | UUID:
    if "__type__" not in obj:
        return obj

    match obj["__type__"]:
        case "__datetime__":
            return parse_date(obj["isoformat"])
        case "__date__":
            return parse_date(obj["isoformat"]).date()
        case "__decimal__":
            return Decimal(obj["decimal"])
        case "__uuid__":
            return UUID(obj["uuid"])
        case _:
            err_msg = f"Unknown type: {obj['__type__']}"
            raise ValueError(err_msg)


def dumps(obj: Any) -> str:
    return json.dumps(obj, cls=XJSONEncoder)


def loads(obj: bytes | str) -> Any:
    return json.loads(obj, object_hook=xjson_decoder)


class XJSONRedisSerializer(BaseSerializer):
    def dumps(self, value: Any) -> bytes:
        return dumps(value).encode()

    def loads(self, value: bytes | str) -> Any:
        return loads(value)
