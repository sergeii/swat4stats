# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .common import *


ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1', '192.168.1.10', '192.168.1.20')

INSTALLED_APPS = INSTALLED_APPS + ('stats7', 'debug_toolbar',)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django',
        'USER': 'django',
        'PASSWORD': 'django',
        'HOST': '192.168.1.10',
        'PORT': '5432',
        'OPTIONS': {},
    },
    'stats': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stats',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '192.168.1.101',
        'OPTIONS': {},
    }
}

DATABASE_ROUTERS = (
    'stats7.router.Router',
)

MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE_CLASSES

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
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join('/tmp', 'debug.log'),
            'formatter': 'simple',
        },
        'sql': {
            'level': 'DEBUG',
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
        'stats7': {
            'handlers': ['debug'],
            'level': 'DEBUG',
            'propagate': True
        },
        'tracker': {
            'handlers': ['debug'],
            'level': 'DEBUG',
            'propagate': True
        },
    },
}

CACHEOPS_REDIS = {
    'host': '192.168.1.101',    # redis-server is on same machine
    'port': 6379,               # default redis port
    'db': 1,                    # SELECT non-default redis database
                                # using separate redis db or redis instance
                                # is highly recommended
    'socket_timeout': 3,
}

DEBUG_TOOLBAR_PATCH_SETTINGS = False
