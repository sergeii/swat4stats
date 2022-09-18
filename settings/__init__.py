import importlib
import os
import sys


STAGE = os.environ.get('STAGE', 'local').lower()

modules = ['common', STAGE]

if 'test' in sys.argv[1:2] or 'py.test' in sys.argv[0] or 'pytest' in sys.argv[0]:
    modules.append('test')

for module in modules:
    settings = importlib.import_module(f'settings.{module}').__dict__
    globals().update(settings)

REDIS_HOST, REDIS_PORT, REDIS_DB = (globals()['REDIS_HOST'],
                                    globals()['REDIS_PORT'],
                                    globals()['REDIS_DB'])


def redis_url(alias):
    db = REDIS_DB[alias]
    return f'redis://{REDIS_HOST}:{REDIS_PORT}/{db}',


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': redis_url('default'),
    },
    'cacheback': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': redis_url('cacheback'),
        'OPTIONS': {
            'serializer': 'utils.xjson.XJSONRedisSerializer',
        },
    },
}

CELERY_BROKER_URL = redis_url('celery')
