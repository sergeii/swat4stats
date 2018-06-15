# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import json

import raven
from raven.transport import ThreadedRequestsHTTPTransport

from .common import *


RAVEN_GIT_SHA = raven.fetch_git_sha(BASE_DIR)

with open(os.path.expanduser('~/secrets.json')) as f:
    SECRETS = json.load(f)

SECRET_KEY = SECRETS['SECRET_KEY']
ALLOWED_HOSTS = ['swat4stats.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'db.int.swat4stats.com',
        'PORT': '6432',
        'NAME': 'swat4stats',
        'USER': 'swat4stats',
        'PASSWORD': SECRETS['DB_PASSWORD'],
        'CONN_MAX_AGE': 600,
        'OPTIONS': {},
    },
}

INSTALLED_APPS += (
    'elasticapm.contrib.django',
)

MIDDLEWARE_CLASSES = (
    'elasticapm.contrib.django.middleware.TracingMiddleware',
) + MIDDLEWARE_CLASSES

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
    'release': RAVEN_GIT_SHA,
    'include_versions': False,
    'transport': ThreadedRequestsHTTPTransport,
}

ELASTIC_APM = {
    'SERVICE_NAME': 'swat4stats',
    'SECRET_TOKEN': '193dde07-bd58-434a-b081-dcb5efed8079',
    'SERVER_URL': 'https://apm-intake.swat4stats.com',
    'ENVIRONMENT': 'production',
    'SERVICE_VERSION': RAVEN_GIT_SHA,
    'TRANSACTION_SAMPLE_RATE': 0.1,
    'SPAN_FRAMES_MIN_DURATION': 0,
    'TRANSACTION_MAX_SPANS': 100,
    'FLUSH_INTERVAL': 30,
    'AUTO_LOG_STACKS': False,
    'COLLECT_LOCAL_VARIABLES': 'off',
}
