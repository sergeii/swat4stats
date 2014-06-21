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
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': PATH_VENV.child('log', 'django.log'),
        'formatter': 'simple',
        'maxBytes': 1024*1024*5,
        'backupCount': 5,
    },
    'stream': {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': PATH_VENV.child('log', 'stream.log'),
        'maxBytes': 1024*1024*50,
        'backupCount': 10,
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

COMPRESS_OFFLINE = True
