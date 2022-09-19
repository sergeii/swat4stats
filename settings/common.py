import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

from settings.utils import env


REDIS_HOST = env('SETTINGS_REDIS_HOST', '127.0.0.1')
REDIS_PORT = env('SETTINGS_REDIS_PORT', 6379)
REDIS_DB = {
    'default': 1,
    'cacheback': 1,
    'celery': 3,
}

BASE_DIR = Path(os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir)))

DEBUG = False

SECRET_KEY = '-secret-'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': env('SETTINGS_DB_HOST', '127.0.0.1'),
        'PORT': env('SETTINGS_DB_PORT', '5432'),
        'USER': env('SETTINGS_DB_USER', 'swat4stats'),
        'PASSWORD': env('SETTINGS_DB_PASSWORD', 'swat4stats'),
        'NAME': env('SETTINGS_DB_NAME', 'swat4stats'),
        'CONN_MAX_AGE': 600,
        'DISABLE_SERVER_SIDE_CURSORS': True,
    }
}

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
    'django_countries',
    'raven.contrib.django.raven_compat',
    'tracker',
)

MIDDLEWARE = (
    'utils.middleware.RealRemoteAddrMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
)

SILENCED_SYSTEM_CHECKS = [
    'models.E034',  # The index name 'X' cannot be longer than 30 characters.
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'tracker.context_processors.current_view',
            ],
        },
    },
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATICFILES_DIRS = (
    str(BASE_DIR / 'web' / 'raw'),
    str(BASE_DIR / 'web' / 'dist'),
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

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SERVER_EMAIL = 'django@swat4stats.com'
DEFAULT_FROM_EMAIL = 'noreply@swat4stats.com'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

if syslog_address := os.environ.get('SETTINGS_SYSLOG_ADDRESS'):
    syslog_host, syslog_port = syslog_address.split(':')
    LOGGING_SYSLOG_ADDRESS = (syslog_host, int(syslog_port))
else:
    LOGGING_SYSLOG_ADDRESS = ('localhost', 514)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'syslog': {
            'format': 'app.swat4tracker.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
        },
        'simple': {
            'format': '[%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(funcName)s() - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'syslog': {
            'level': 'DEBUG',
            'formatter': 'syslog',
            'class': 'logging.handlers.SysLogHandler',
            'address': LOGGING_SYSLOG_ADDRESS,
        },
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {},
}

CACHEBACK_CACHE_ALIAS = 'cacheback'

# celery
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ['xjson']
CELERY_RESULT_SERIALIZER = 'xjson'
CELERY_EVENT_SERIALIZER = 'xjson'
CELERY_TASK_SERIALIZER = 'xjson'
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_TASK_ANNOTATIONS = {
    'cacheback.tasks.refresh_cache': {
        'expires': 600,
        'time_limit': 60,
    },
}
CELERY_BEAT_SCHEDULE = {
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
    'update-positions': {
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

RAVEN_CONFIG = {}

# list pf case-insensitive regex patterns used to describe a popular name
# in order to exclude it from a name isp profile lookup
TRACKER_POPULAR_NAMES = (
    r'^todosetname',
    r'^player',
    r'^newname',
    r'^afk',
    r'^giocatore',
    r'^jogador',
    r'^jugador',
    r'^joueur',
    r'^spieler',
    r'^gracz',
    r'^test',
    r'^\|\|$',
    r'^lol$',
    r'^swat$',
    r'^swat4$',
    r'^suspect$',
    r'^noob$',
    r'^n00b$',
    r'^vip$',
    r'^xxx$',
    r'^killer$',
    r'^david$',
    r'^pokemon$',
    r'^rambo$',
    r'^ghost$',
    r'^hitman$',
    r'^wolf$',
    r'^sniper$',
)
