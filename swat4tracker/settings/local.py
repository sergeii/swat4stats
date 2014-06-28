# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)

STATIC_ROOT = PATH_VENV.child('static')
MEDIA_ROOT = PATH_VENV.child('media')

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

LOGGING['handlers'].update({
    'django': {
        'level': 'WARNING',
        'class': 'logging.FileHandler',
        'filename': os.path.join('/tmp', '%s_debug.log' % PATH_PROJECT.name),
        'formatter': 'simple',
    },
    'sql': {
        'level': 'WARNING',
        'class': 'logging.FileHandler',
        'filename': os.path.join('/tmp', '%s_sql.log' % PATH_PROJECT.name),
    },
    'console': {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    },
    'stream': {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': os.path.join('/tmp', '%s_stream.log' % PATH_PROJECT.name),
    },
})

LOGGING['loggers'].update({
    'django': {
        'handlers': ['django'],
        'level': 'WARNING',
        'propagate': True,
    },
    'tracker': {
        'handlers': ['django'],
        'level': 'WARNING',
        'propagate': True
    },
    'django.db.backends': {
        'handlers': ['sql'],
        'level': 'WARNING',
        'propagate': False,
    },
})

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
