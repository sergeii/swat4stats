# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)

STATIC_ROOT = PATH_VENV.child('static')
MEDIA_ROOT = PATH_VENV.child('media')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'swat4tracker',
        'USER': 'swat4tracker',
        'PASSWORD': 'swat4tracker',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'OPTIONS': {},
    }
}

CACHES['default'] = {
    'BACKEND': 'redis_cache.cache.RedisCache',
    'LOCATION': '127.0.0.1:6379:1',
}

CACHEOPS_REDIS = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 2,
    'socket_timeout': 3,
}

COMPRESS_OFFLINE = False
