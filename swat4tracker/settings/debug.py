# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .local import *

DEBUG = True
TEMPLATE_DEBUG = True

INTERNAL_IPS = INTERNAL_IPS + ('192.168.1.10', '192.168.1.20')
INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE_CLASSES

LOGGING['loggers'].update({
    'django': {
        'handlers': ['syslog', 'mail_admins'],
        'level': 'INFO',
    },
    'tracker': {
        'handlers': ['syslog', 'mail_admins'],
        'level': 'DEBUG',
        'propagate': False
    },
    'django.db.backends': {
        'handlers': ['syslog'],
        'level': 'DEBUG',
        'propagate': False,
    },
})

DEBUG_TOOLBAR_PATCH_SETTINGS = False
