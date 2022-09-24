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

BASE_DIR = Path(os.path.dirname(__file__)).resolve().parent

DEBUG = False

SECRET_KEY = 'secret'

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
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': env('SETTINGS_DB_REPLICA_HOST', '127.0.0.1'),
        'PORT': env('SETTINGS_DB_REPLICA_PORT', '5432'),
        'USER': env('SETTINGS_DB_REPLICA_USER', 'swat4stats'),
        'PASSWORD': env('SETTINGS_DB_REPLICA_PASSWORD', 'swat4stats'),
        'NAME': env('SETTINGS_DB_REPLICA_NAME', 'swat4stats'),
        'CONN_MAX_AGE': 600,
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'TEST': {
            'MIRROR': 'default',
        },
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

    'cacheback',
    'django_countries',
    'django_filters',
    'rest_framework',
    'raven.contrib.django.raven_compat',

    'apps.tracker',
    'apps.news',
    'apps.geoip',
    'apps.utils',
    'apps.api',
)

SILENCED_SYSTEM_CHECKS = [
    'models.E034',  # The index name 'X' cannot be longer than 30 characters.
]

MIDDLEWARE = (
    'apps.utils.middleware.RealRemoteAddrMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(BASE_DIR / 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'apps.utils.context_processors.settings',
                'apps.utils.context_processors.current_view',
            ],
        },
    },
]

STATICFILES_STORAGE = 'apps.utils.staticfiles.ManifestStaticFilesStorage'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATICFILES_DIRS = (
    BASE_DIR / 'assets',
)

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = BASE_DIR / 'static'
MEDIA_ROOT = BASE_DIR / 'media'

LOCALE_PATHS = (
    BASE_DIR / 'locale',
)

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

TIME_FORMAT = 'H:i'

ROOT_URLCONF = 'swat4stats.urls'
WSGI_APPLICATION = 'swat4stats.wsgi.application'

ALLOWED_HOSTS = []
INTERNAL_IPS = ()

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

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
            'format': 'app.swat4stats.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
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
CACHEBACK_TASK_IGNORE_RESULT = True

# celery
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ['json', 'xjson']
CELERY_TASK_SERIALIZER = 'xjson'
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_TASK_ROUTES = {
    'cacheback.tasks.refresh_cache': {
        'queue': 'cacheback',
    },
}
CELERY_TASK_ANNOTATIONS = {
    'cacheback.tasks.refresh_cache': {
        'expires': 600,
        'time_limit': 60,
    },
}
CELERY_BEAT_SCHEDULE = {
    'discover_servers': {
        'task': 'discover_servers',
        'schedule': timedelta(seconds=5 * 60),
        'options': {
            'expires': 2 * 60,
            'time_limit': 60,
            'rate_limit': '12/h',
        },
    },
    'discover_extra_query_ports': {
        'task': 'discover_extra_query_ports',
        'schedule': timedelta(seconds=10 * 60),
        'options': {
            'expires': 5 * 60,
            'time_limit': 300,
            'rate_limit': '6/h',
        },
    },
    'refresh_listed_servers': {
        'task': 'refresh_listed_servers',
        'schedule': timedelta(seconds=5),
        'options': {
            'time_limit': 3,
            'expires': 2,
        },
    },
    'update_player_preferences': {
        'task': 'update_player_preferences',
        'schedule': crontab(minute=15),
        'options': {
            'expires': 15 * 60,
        },
    },
    'update_player_stats': {
        'task': 'update_player_stats',
        'schedule': crontab(minute=0),
        'options': {
            'expires': 30 * 60,
        },
    },
    'update_player_positions': {
        'task': 'update_player_positions',
        'schedule': crontab(hour='*/6', minute=30),
        'options': {
            'expires': 2 * 60*60,
        },
    },
    'settle_annual_player_positions': {
        'task': 'settle_annual_player_positions',
        'schedule': crontab(hour=6, minute=45, day_of_month='1-3', month_of_year=1),
        'options': {
            'expires': 12 * 60*60,
        },
    },
    'delete_expired_ips': {
        'task': 'delete_expired_ips',
        'schedule': crontab(hour=10, minute=20),
        'options': {
            'expires': 12 * 60*60,
        },
    }
}

RAVEN_CONFIG = {}

REST_FRAMEWORK = {
    # builtin settings
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'apps.utils.throttling.MethodScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'servers': '10/minute',
    },
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.api.pagination.CursorPagination',
    'EXCEPTION_HANDLER': 'apps.utils.views.exception_handler',
    'PAGE_SIZE': 20,
}


# tracker settings
##

# how much seconds into past is considered recent for a player
TRACKER_RECENT_TIME = 3600 * 24 * 180
# number of the latest games to aggregate preferences over
TRACKER_PREFERRED_GAMES = 25
# min number of players a game round to be considered qualified
TRACKER_MIN_PLAYERS = 10
# min number of weapon shots required
# for aggregation of weapon related stats (e.g. accuracy)
TRACKER_MIN_WEAPON_SHOTS = 1000
# same for grenades
TRACKER_MIN_GRENADE_SHOTS = 100
# min kills for kill based ratio
TRACKER_MIN_KILLS = 100

# min time for score per minute and other time based ratio
TRACKER_MIN_TIME = 6 * 60*60
# min time for round based stats
TRACKER_MIN_GAMES = 50

# min ammo required for accuracy calculation in a single game round
TRACKER_MIN_GAME_AMMO = 60
TRACKER_MIN_GAME_GRENADES = 10

# max number of concurrent server status requests
TRACKER_STATUS_CONCURRENCY = 200
# time a task should be waited for
TRACKER_STATUS_TIMEOUT = 0.5
# max number of failures a server considered offline
TRACKER_STATUS_FAILURES = 12
# min day to make new appear in leaderboards
TRACKER_MIN_YEAR_DAY = 15

TRACKER_MIN_NAME_LEN = 3  # name with length shorter than this number is considered popular.
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

re_ipv4 = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
re_port = r'\d{1,5}'

# a list of (url, regex pattern (for extracting ip and port)) tuples
# used by the tasks.update_server_list task to keep the server list up to date
TRACKER_SERVER_DISCOVERY = (
    # mark server list
    ('https://www.markmods.com/swat4serverlist/',
        fr'\b(?P<addr>{re_ipv4}):(?P<port>{re_port})\b'),
    # clan pages
    ('http://mytteam.com/',
        fr'\b(?P<addr>{re_ipv4}):(?P<port>{re_port})\b'),
) + tuple(
    # gametracker
    (f'https://www.gametracker.com/search/swat4/?&searchipp=50&searchpge={page}',
        fr'\b(?P<addr>{re_ipv4}):(?P<port>{re_port})\b')
    for page in range(1, 4)
)
TRACKER_SERVER_DISCOVERY_TIMEOUT = 10

TRACKER_SERVER_REDIS_KEY = 'servers'

# keep IPs for this number of seconds
GEOIP_IP_EXPIRY = 180*24*60*60
# do extra whois request in case existing ip range is too large
GEOIP_ACCEPTED_IP_LENGTH = 256*256*64
