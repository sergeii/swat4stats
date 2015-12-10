# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import raven

from .common import *

SECRET_KEY = os.environ['DJ_SECRET_KEY']
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

INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

STATIC_ROOT = Path('/var/www/static/swat4tracker/')
MEDIA_ROOT = Path('/var/www/media/swat4tracker/')

CACHES['default'] = {
    'BACKEND': 'django_redis.cache.RedisCache',
    'LOCATION': 'unix:/var/run/redis/redis.sock:1',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'syslog': {
            'format': 'swat4tracker.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
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
            'propagate': True,
        },
        'django': {
            'propagate': True,
        },
    },
}

CACHEOPS_REDIS = {
    'unix_socket_path': '/var/run/redis/redis.sock',
    'db': 2,
}

COMPRESS_OFFLINE = True

if os.environ.get('DJ_SENTRY_DSN'):
    RAVEN_CONFIG = {
        'dsn': os.environ['DJ_SENTRY_DSN'],
        'auto_log_stacks': True,
        'release': raven.fetch_git_sha(BASE_DIR),
    }
