# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .local import *

DEBUG = True
TEMPLATE_DEBUG = True

#INTERNAL_IPS = INTERNAL_IPS + ('192.168.1.10', '192.168.1.20')
INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE_CLASSES

LOGGING['handlers'].update({
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
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    },
})

DEBUG_TOOLBAR_PATCH_SETTINGS = False