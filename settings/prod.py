import os

from raven.transport import ThreadedRequestsHTTPTransport

from .common import LOGGING
from .utils import env

SECRET_KEY = env('SETTINGS_SECRET_KEY', '-secret-')

ALLOWED_HOSTS = ['.swat4stats.com']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
SERVER_EMAIL = 'django@dev.swat4stats.com'
DEFAULT_FROM_EMAIL = 'noreply@dev.swat4stats.com'

STATIC_ROOT = '/app/static'

LOGGING.update({
    'loggers': {
        '': {
            'level': 'DEBUG',
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
        'django': {
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'level': 'INFO',
            'propagate': True,
        },
        'py.warnings': {
            'level': 'INFO',
            'handlers': ['syslog'],
            'propagate': False,
        },
    }
})

RAVEN_CONFIG = {
    'dsn': env('SETTINGS_SENTRY_DSN', '-secret-'),
    'auto_log_stacks': True,
    'release': os.environ.get('GIT_RELEASE_VER'),
    'include_versions': False,
    'transport': ThreadedRequestsHTTPTransport,
    'processors': (),
}
