import json
from collections import OrderedDict
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from uuid import UUID

from dateutil.parser import parse as parse_date
from django.core.serializers.base import DeserializedObject
from django_redis.serializers.base import BaseSerializer


class XJSONEncoder(json.JSONEncoder):

    def default(self, obj):

        if isinstance(obj, datetime):
            return OrderedDict([
                ('__type__', '__datetime__'),
                ('isoformat', obj.isoformat()),
            ])
        elif isinstance(obj, date):
            return OrderedDict([
                ('__type__', '__date__'),
                ('isoformat', obj.isoformat()),
            ])
        elif isinstance(obj, Decimal):
            return OrderedDict([
                ('__type__', '__decimal__'),
                ('decimal', str(obj)),
            ])
        elif isinstance(obj, UUID):
            return OrderedDict([
                ('__type__', '__uuid__'),
                ('uuid', str(obj)),
            ])
        elif isinstance(obj, DeserializedObject):
            return self.default(obj.object)

        return super().default(obj)


def xjson_decoder(obj: dict) -> dict | datetime | date | Decimal | UUID:
    if '__type__' in obj:

        if obj['__type__'] == '__datetime__':
            return parse_date(obj['isoformat'])

        elif obj['__type__'] == '__date__':
            return parse_date(obj['isoformat']).date()

        elif obj['__type__'] == '__decimal__':
            return Decimal(obj['decimal'])

        elif obj['__type__'] == '__uuid__':
            return UUID(obj['uuid'])

    return obj


def dumps(obj: Any) -> str:
    return json.dumps(obj, cls=XJSONEncoder)


def loads(obj: bytes | str) -> Any:
    return json.loads(obj, object_hook=xjson_decoder)


class XJSONRedisSerializer(BaseSerializer):

    def dumps(self, value: Any) -> bytes:
        return dumps(value).encode()

    def loads(self, value: bytes | str) -> Any:
        return loads(value)
