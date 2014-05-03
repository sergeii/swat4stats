# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
from unipath import Path

# swat4tracker project package
PATH_PROJECT = Path(os.path.dirname(__file__)).parent
# django application package
PATH_APP = PATH_PROJECT.parent
# virtualenv dir
PATH_VENV = PATH_APP.parent

DEBUG = False
TEMPLATE_DEBUG = False

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'south',
    'cacheops',
    'django_countries',
    
    'tracker',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth', 
    'django.core.context_processors.debug', 
    'django.core.context_processors.i18n', 
    'django.core.context_processors.media', 
    'django.core.context_processors.static', 
    'django.core.context_processors.tz', 
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request', 

    'tracker.context_processors.current_view', 
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder', 
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)

STATIC_URL = '/static/'
STATIC_ROOT = PATH_VENV.child('static')

MEDIA_URL = '/media/'
MEDIA_ROOT = PATH_VENV.child('media')

TEMPLATE_DIRS = (
    PATH_APP.child('templates'),
)

STATICFILES_DIRS = (
    PATH_APP.child('static'),
)

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

TIME_FORMAT = 'H:i'

ROOT_URLCONF = 'swat4tracker.urls'
WSGI_APPLICATION = 'swat4tracker.wsgi.application'

SECRET_KEY = 'gtnc%v99=-*!a@t+et@7tzc^20_y)z!swb9!nu0zn1)%om^x-z'

ALLOWED_HOSTS = []
INTERNAL_IPS = ()

ADMINS = (
    ('Sergei', 'kh.sergei@gmail.com'),
)

MANAGERS = (
    ('Sergei', 'kh.sergei@gmail.com'),
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

CACHEOPS = {
    #'auth.user': ('get', 60*15),
    #'auth.*': ('all', 60*60),
    #'*.*': ('count', 60*15),
    'tracker.*': ('just_enable', None),
}