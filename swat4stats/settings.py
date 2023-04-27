import logging
import os
from datetime import timedelta
from pathlib import Path
import warnings

from celery.schedules import crontab
from django.utils.deprecation import RemovedInDjango50Warning

from apps.utils.settings import env, env_bool, env_list, env_log_level


warnings.simplefilter('ignore', RemovedInDjango50Warning)
warnings.simplefilter('ignore', DeprecationWarning)


def redis_url(alias: str) -> str:
    db = REDIS_DB[alias]
    return f'redis://{REDIS_HOST}:{REDIS_PORT}/{db}'


REDIS_HOST = env('SETTINGS_REDIS_HOST', '127.0.0.1')
REDIS_PORT = env('SETTINGS_REDIS_PORT', 6379)
REDIS_DB = {
    'default': int(env('SETTINGS_REDIS_CACHE_DB', 1)),
    'cacheback': int(env('SETTINGS_REDIS_CACHE_DB', 1)),
}

EMAIL_BACKENDS = {
    'console': 'django.core.mail.backends.console.EmailBackend',
    'smtp': 'django.core.mail.backends.smtp.EmailBackend',
}

BASE_DIR = Path(os.path.dirname(__file__)).resolve().parent

ALLOWED_HOSTS = env_list('SETTINGS_ALLOWED_HOSTS')

DEBUG = env_bool('SETTINGS_DEBUG', False)

if DEBUG:
    INTERNAL_IPS = ('127.0.0.1',)
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: request.META.get('HTTP_X_DDT') == '1'
    }

SECRET_KEY = env('SETTINGS_SECRET_KEY', '-secret-')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': redis_url('default'),
    },
    'cacheback': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': redis_url('cacheback'),
        'OPTIONS': {
            'SERIALIZER': 'apps.utils.xjson.XJSONRedisSerializer',
        },
    },
}

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

INSTALLED_APPS: tuple[str, ...] = (
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

    'apps.tracker',
    'apps.news',
    'apps.geoip',
    'apps.utils',
    'apps.api',
)

if DEBUG:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)

MIDDLEWARE: tuple[str, ...] = (
    'apps.utils.middleware.RealRemoteAddrMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
)

if DEBUG:
    MIDDLEWARE = (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        'apps.utils.middleware.ProfileMiddleware',
    ) + MIDDLEWARE

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

SILENCED_SYSTEM_CHECKS = [
    'models.E034',  # The index name 'X' cannot be longer than 30 characters.
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

STATIC_ROOT = env('SETTINGS_STATIC_ROOT', BASE_DIR / 'static')
MEDIA_ROOT = env('SETTINGS_MEDIA_ROOT', BASE_DIR / 'media')

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

USE_X_FORWARDED_HOST = True

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

EMAIL_BACKEND = EMAIL_BACKENDS[env('SETTINGS_EMAIL_BACKEND_ALIAS', 'console')]
EMAIL_HOST = env('SETTINGS_EMAIL_HOST', 'localhost')
EMAIL_PORT = int(env('SETTINGS_EMAIL_PORT', 25))
EMAIL_HOST_USER = env('SETTINGS_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('SETTINGS_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('SETTINGS_EMAIL_USE_TLS', False)

SERVER_EMAIL = env('SETTINGS_SERVER_EMAIL', 'django@swat4stats.com')
DEFAULT_FROM_EMAIL = env('SETTINGS_DEFAULT_FROM_EMAIL', 'noreply@swat4stats.com')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

if syslog_address := env('SETTINGS_SYSLOG_ADDRESS', None):
    syslog_host, syslog_port = syslog_address.split(':')
    default_logging_handler = {
        'level': 'DEBUG',
        'formatter': 'syslog',
        'class': 'logging.handlers.SysLogHandler',
        'address': (syslog_host, int(syslog_port)),
    }
else:
    default_logging_handler = {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'formatter': 'simple'
    }

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
        'default': default_logging_handler,
        'mail_admins': {
            'level': 'ERROR',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'level': env_log_level('SETTINGS_LOG_LEVEL', 'INFO'),
            'handlers': ['default'],
        },
        'django.db.backends': {
            'level': env_log_level('SETTINGS_LOG_LEVEL', 'INFO', logging.WARNING),
            'handlers': ['default'],
            'propagate': False,
        },
        'factory': {
            'level': env_log_level('SETTINGS_LOG_LEVEL', 'INFO', logging.ERROR),
            'handlers': ['default'],
            'propagate': False,
        },
    },
}

CACHEBACK_CACHE_ALIAS = 'cacheback'
CACHEBACK_TASK_IGNORE_RESULT = True

# celery
CELERY_BROKER_URL = env('SETTINGS_CELERY_BROKER_URL', 'memory://')
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = env_list('SETTINGS_CELERY_ACCEPT_CONTENT') or ['json', 'xjson']
CELERY_TASK_SERIALIZER = 'xjson'
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

if env_bool('SETTINGS_CELERY_TASK_ALWAYS_EAGER', False) and DEBUG:
    CELERY_TASK_ALWAYS_EAGER = True

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
    'discover_published_servers': {
        'task': 'discover_published_servers',
        'schedule': timedelta(seconds=5 * 60),
        'options': {
            'expires': 2 * 60,
            'time_limit': 60,
            'rate_limit': '12/h',
        },
    },
    'discover_good_query_ports': {
        'task': 'discover_good_query_ports',
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
            'time_limit': 5,
            'expires': 5,
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
    'merge_server_stats': {
        'task': 'merge_server_stats',
        'schedule': crontab(hour='*/2', minute=30),
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
    'EXCEPTION_HANDLER': 'apps.api.utils.exception_handler',
    'PAGE_SIZE': 20,
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

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
TRACKER_MIN_KILLS = 500

# min time for score per minute and other time based ratio
TRACKER_MIN_TIME = 10 * 60*60
# min time for round based stats
TRACKER_MIN_GAMES = 100

# min ammo required for accuracy calculation in a single game round
TRACKER_MIN_GAME_AMMO = 60
TRACKER_MIN_GAME_GRENADES = 10

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

TRACKER_SERVER_DISCOVERY_SOURCES = (
    {
        'url': 'https://www.markmods.com/swat4serverlist/',
        'parser': 'apps.tracker.discovery.plain_ip_port',
    },
    {
        'url': 'https://mytteam.com/',
        'parser': 'apps.tracker.discovery.plain_ip_port',
    },
    {
        'url': 'https://master.swat4stats.com/api/servers',
        'parser': 'apps.tracker.discovery.master_server_api'
    },
)
TRACKER_SERVER_DISCOVERY_HTTP_TIMEOUT = 5
TRACKER_SERVER_DISCOVERY_PROBE_CONCURRENCY = 10

TRACKER_STATUS_REDIS_KEY = 'servers'
# max number of concurrent server status requests
TRACKER_STATUS_QUERY_CONCURRENCY = 100
TRACKER_STATUS_QUERY_TIMEOUT = 1
# max number of accumulated failures before a server is considered offline
TRACKER_STATUS_TOLERATED_FAILURES = 12

# because we test many ports of a single server at once,
# limit the number of total concurrent requests
TRACKER_PORT_DISCOVERY_CONCURRENCY = 20

# keep IPs for this number of seconds
GEOIP_IP_EXPIRY = 180*24*60*60
# do extra whois request in case existing ip range is too large
GEOIP_ACCEPTED_IP_LENGTH = 256*256*64
