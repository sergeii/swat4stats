import os
import sys
import warnings
from importlib import import_module

from django.utils.deprecation import RemovedInDjango50Warning


warnings.simplefilter('ignore', RemovedInDjango50Warning)
warnings.simplefilter('ignore', DeprecationWarning)


STAGE = os.environ.get('STAGE', 'local').lower()

modules = ['common', STAGE]

if 'test' in sys.argv[1:2] or 'py.test' in sys.argv[0] or 'pytest' in sys.argv[0]:
    modules.append('test')

for module in modules:
    settings = import_module(f'settings.{module}').__dict__
    globals().update(settings)


REDIS_HOST, REDIS_PORT, REDIS_DB = (globals()['REDIS_HOST'],
                                    globals()['REDIS_PORT'],
                                    globals()['REDIS_DB'])


def redis_url(alias):
    db = REDIS_DB[alias]
    return f'redis://{REDIS_HOST}:{REDIS_PORT}/{db}',


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': redis_url('default'),
    },
    'cacheback': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': redis_url('cacheback'),
        'OPTIONS': {
            'SERIALIZER': 'apps.utils.xjson.XJSONRedisSerializer',
        },
    },
}

CELERY_BROKER_URL = redis_url('celery')
