# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s()] - %(message)s'
        },
    },
    'handlers': {
        'debug': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join('/tmp', 'debug.log'),
            'formatter': 'simple',
        },
        'sql': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join('/tmp', 'sql.log'),
        },
        'console':{
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['sql'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['debug'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'tracker': {
            'handlers': ['debug', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
    },
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