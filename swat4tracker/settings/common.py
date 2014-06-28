# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
from datetime import timedelta

from unipath import Path
from celery.schedules import crontab

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
    'django.contrib.sites',
    'django.contrib.sitemaps',

    'south',
    'cacheops',
    'django_countries',
    'compressor',
    'django_markdown',
    'django_nose',
    
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
    'tracker.context_processors.current_site', 
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder', 
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

TEMPLATE_DIRS = (
    PATH_APP.child('templates'),
)

STATICFILES_DIRS = (
    PATH_APP.child('static'),
)

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

TIME_FORMAT = 'H:i'

ROOT_URLCONF = 'swat4tracker.urls'
WSGI_APPLICATION = 'swat4tracker.wsgi.application'

ALLOWED_HOSTS = []
INTERNAL_IPS = ()

SITE_ID = 1

ADMINS = (
    ('Sergei', 'kh.sergei@gmail.com'),
)

MANAGERS = ADMINS

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s()] - %(message)s'
        },
    },
    'handlers': {
        # implement stream handler
    },
    'loggers': {
        'stream': {
            'handlers': ['stream'],
            'level': 'INFO',
            'propagate': False
        },
    },
}

CACHEOPS = {
    'tracker.*': ('just_enable', None),
}

COMPRESS_ENABLED = True
COMPRESS_OUTPUT_DIR = ''

COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.datauri.CssDataUriFilter',
    'compressor.filters.cssmin.CSSMinFilter',
)

COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio'),
    ('text/less', 'lessc {infile} {outfile}'),
)

# only data-encode small files
COMPRESS_DATA_URI_MAX_SIZE = 1024*5

MARKDOWN_PROTECT_PREVIEW = True

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# celery
BROKER_URL = 'redis://localhost/3'
CELERY_RESULT_BACKEND = 'redis://localhost/4'

CELERYBEAT_SCHEDULE = {
    # fetch new servers from various sources every 30 min
    'update-servers': {
        'task': 'tracker.tasks.update_server_list',
        'schedule': timedelta(minutes=30),
    },
    # query servers for 90 seconds with an interval of 5 seconds
    'query-servers': {
        'task': 'tracker.tasks.query_listed_servers',
        'schedule': timedelta(seconds=90),
        'kwargs': {'time_delta': 90, 'interval': 5},
    },
    # update the profile popular fields (name, team, etc) every hour
    'update-popular': {
        'task': 'tracker.tasks.update_popular',
        'schedule': crontab(minute='10'),
        'kwargs': {'time_delta': timedelta(hours=2)},
    },
    # update profile ranks every 2 hours
    'update-ranks': {
        'task': 'tracker.tasks.update_ranks',
        'schedule': crontab(minute='20', hour='*/2'),
        'kwargs': {'time_delta': timedelta(hours=4)},
    },
    # update positions every 6 hours
    'update-ranks': {
        'task': 'tracker.tasks.update_positions',
        'schedule': crontab(minute='30', hour='*/6'),
    },
    # update past year positions on the new year's jan 1st 6 am
    'update-ranks-past-year': {
        'task': 'tracker.tasks.update_positions',
        'schedule': crontab(minute='0', hour='6', day_of_month='1', month_of_year='1'),
        'args': (-1,),
    },
}

CELERY_ROUTES = {
    # use a dedicated queue for server queries
    'tracker.tasks.query_listed_servers': {
        'queue': 'serverquery',
    },
}

CELERY_TASK_RESULT_EXPIRES = 60
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT = ['pickle']
# dont reserve tasks
CELERYD_PREFETCH_MULTIPLIER = 1
