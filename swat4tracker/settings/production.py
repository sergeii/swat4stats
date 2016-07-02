# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os
import json

import raven
from raven.transport import ThreadedRequestsHTTPTransport

from .common import *

with open(os.path.expanduser('~/secrets.json')) as f:
    SECRETS = json.load(f)

SECRET_KEY = SECRETS['SECRET_KEY']
ALLOWED_HOSTS = ['swat4stats.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'db.int.swat4stats.com',
        'PORT': '5432',
        'NAME': 'swat4stats',
        'USER': 'swat4stats',
        'PASSWORD': SECRETS['DB_PASSWORD'],
        'OPTIONS': {},
    },
}

STATIC_ROOT = '/home/swat4stats/static'

CACHES['default'] = {
    'BACKEND': 'django_redis.cache.RedisCache',
    'LOCATION': 'redis://127.0.0.1:6379/1',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'syslog': {
            'format': 'swat4stats.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
        'syslog': {
            'level': 'DEBUG',
            'formatter': 'syslog',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log'
        },
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'handlers': ['syslog', 'sentry'],
        },
        'django.db.backends': {
            'level': 'WARNING',
            'handlers': ['syslog', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'WARNING',
            'handlers': ['syslog'],
            'propagate': False,
        },
        'django.request': {
            'propagate': True,
        },
        'django.security': {
            'propagate': True,
        },
        'py.warnings': {
            'level': 'INFO',
            'handlers': ['syslog'],
            'propagate': False,
        },
        'django': {
            'propagate': True,
        },
    },
}

CACHEOPS_REDIS = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 2,
}

COMPRESS_OFFLINE = True

RAVEN_CONFIG = {
    'dsn': SECRETS['SENTRY_DSN'],
    'auto_log_stacks': True,
    'release': raven.fetch_git_sha(BASE_DIR),
    'include_versions': False,
    'transport': ThreadedRequestsHTTPTransport,
}
