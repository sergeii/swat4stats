from .common import LOGGING, REST_FRAMEWORK, INSTALLED_APPS, MIDDLEWARE

DEBUG = True

ALLOWED_HOSTS = ['.swat4stats.test', 'localhost', 'runserver', 'nginx']
INTERNAL_IPS = ('127.0.0.1',)

INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'apps.utils.middleware.ProfileMiddleware',
) + MIDDLEWARE

LOGGING.update({
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'stream': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
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
            'propagate': True,
        },
        'django': {
            'level': 'INFO',
            'propagate': True,
        },
        'factory': {
            'level': 'WARNING',
            'propagate': True,
        },
    }
})

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

DEBUG_TOOLBAR_PATCH_SETTINGS = False

TRACKER_STATUS_TIMEOUT = 1
TRACKER_STATUS_EXPIRY = 3600
