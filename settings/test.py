from settings.common import LOGGING


REDIS_DB = {
    'default': 11,
    'cacheback': 11,
    'celery': 13,
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

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
