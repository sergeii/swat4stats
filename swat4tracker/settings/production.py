# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'NAME': 'swat4tracker',
        'USER': 'swat4tracker',
        'PASSWORD': 'eXaYXS0z0U1aR66X',
        'OPTIONS': {},
    },
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
        'error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': PATH_VENV.child('log', 'django.err.log'),
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['error'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'tracker': {
            'handlers': ['error'],
            'level': 'DEBUG',
            'propagate': True
        },
    },
}

CACHEOPS_REDIS = {
    'unix_socket_path': '/var/run/redis/redis.sock',
    'db': 3,
    #'socket_timeout': 3,
}

ALLOWED_HOSTS = ['swat4stats.com', 'swat4tracker.com']
