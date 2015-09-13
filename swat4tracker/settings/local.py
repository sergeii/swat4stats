# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import sys

from .common import *


ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)

STATIC_ROOT = BASE_DIR.child('static')
MEDIA_ROOT = BASE_DIR.child('media')

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'syslog': {
            'format': 'swat4tracker.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
        },
        'simple': {
            'format': '[%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(funcName)s() - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
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
            'level': 'DEBUG',
            'handlers': ['syslog', 'console'],
        },
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['syslog'],
            'propagate': False,
        },
    },
}


CACHES['default'] = {
    'BACKEND': 'django_redis.cache.RedisCache',
    'LOCATION': 'redis://127.0.0.1:6379/1',
}

CACHEOPS_REDIS = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 2,
    'socket_timeout': 3,
}

COMPRESS_OFFLINE = False


if 'test' in sys.argv[1:2]:
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    LOGGING.update({
        'loggers': {
            '': {
                'level': 'DEBUG',
                'handlers': ['null'],
            },
        },
        'handlers': {
            'null': {
                'class': 'logging.NullHandler'
            }
        }
    })
