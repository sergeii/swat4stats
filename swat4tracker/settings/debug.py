# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .local import *

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE_CLASSES

LOGGING['loggers'] = {
    '': {
        'handlers': ['console', 'syslog'],
        'level': 'DEBUG',
        'propagate': False
    },
    'stream': {
        'handlers': ['console', 'syslog'],
        'level': 'DEBUG',
        'propagate': False
    },
    'django.db.backends': {
        'handlers': ['console', 'syslog'],
        'level': 'INFO',
        'propagate': False,
    },
}

DEBUG_TOOLBAR_PATCH_SETTINGS = False
