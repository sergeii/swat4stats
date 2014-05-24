# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *

ALLOWED_HOSTS = ['swat4tracker.com', 'swat4stats.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'NAME': 'swat4tracker',
        'USER': 'swat4tracker',
        'PASSWORD': 'swat4tracker',
        'OPTIONS': {},
    },
}

LOGGING['handlers'].update({
    'django': {
        'level': 'WARNING',
        'class': 'logging.FileHandler',
        'filename': PATH_VENV.child('log', 'django.log'),
        'formatter': 'simple',
    },
    'stream': {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': PATH_VENV.child('log', 'stream.log'),
    },
})

STATIC_ROOT = Path('/var/www/static/swat4tracker/')
MEDIA_ROOT = Path('/var/www/media/swat4tracker/')

CACHES['default'] = {
    'BACKEND': 'redis_cache.cache.RedisCache',
    'LOCATION': 'unix:/var/run/redis/redis.sock:1',
}

CACHEOPS_REDIS = {
    'unix_socket_path': '/var/run/redis/redis.sock',
    'db': 2,
}
