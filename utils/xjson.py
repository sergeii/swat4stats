import json
from collections import OrderedDict
from datetime import datetime, date

from dateutil.parser import parse as parse_date
from django.core import serializers
from django.core.serializers.base import DeserializedObject
from django.db.models import Model
from django.utils.encoding import force_bytes
from django.core.cache.backends.redis import RedisSerializer as BaseSerializer


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
        elif isinstance(obj, Model):
            return OrderedDict([
                ('__type__', '__model__'),
                ('serialized', serializers.serialize('json', [obj])),
            ])
        elif isinstance(obj, DeserializedObject):
            return self.default(obj.object)

        return super().default(obj)


def xjson_decoder(obj):

    if '__type__' in obj:

        if obj['__type__'] == '__datetime__':
            return parse_date(obj['isoformat'])

        elif obj['__type__'] == '__date__':
            return parse_date(obj['isoformat']).date()

        elif obj['__type__'] == '__model__':
            return list(serializers.deserialize('json', obj['serialized']))[0],

    return obj


def dumps(obj):
    return json.dumps(obj, cls=XJSONEncoder)


def loads(obj):
    if isinstance(obj, bytes):
        obj = obj.decode()
    return json.loads(obj, object_hook=xjson_decoder)


class XJSONRedisSerializer(BaseSerializer):

    def dumps(self, value):
        return force_bytes(dumps(value))

    def loads(self, value):
        return loads(value)
