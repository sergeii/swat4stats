from settings.common import LOGGING


REDIS_DB = {
    'default': 11,
    'cacheback': 11,
    'celery': 13,
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'swat4stats',
        'USER': 'swat4stats',
        'PASSWORD': 'swat4stats',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'DISABLE_SERVER_SIDE_CURSORS': True,
    }
}

LOGGING.update({
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['null'],
        },
        'faker': {
            'level': 'ERROR',
            'handlers': ['null'],
        },
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler'
        }
    }
})

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
