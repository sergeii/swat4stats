import logging
import os
from pathlib import Path

from utils.settings import env, env_bool, env_log_level, env_list


def redis_url(alias):
    db = REDIS_DB[alias]
    return f'redis://{REDIS_HOST}:{REDIS_PORT}/{db}',


REDIS_HOST = env('SETTINGS_REDIS_HOST', '127.0.0.1')
REDIS_PORT = env('SETTINGS_REDIS_PORT', 6379)
REDIS_DB = {
    'default': 1,
}


EMAIL_BACKENDS = {
    'console': 'django.core.mail.backends.console.EmailBackend',
    'smtp': 'django.core.mail.backends.smtp.EmailBackend',
}

BASE_DIR = Path(os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir)))

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
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': redis_url('default'),
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
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django_countries',
    'tracker',
)

if DEBUG:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)

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

if DEBUG:
    MIDDLEWARE = (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ) + MIDDLEWARE

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

SILENCED_SYSTEM_CHECKS = [
    'models.E034',  # The index name 'X' cannot be longer than 30 characters.
]

STATICFILES_STORAGE = 'utils.staticfiles.ManifestStaticFilesStorage'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_DIRS = (
    str(BASE_DIR / 'web' / 'raw'),
    str(BASE_DIR / 'web' / 'dist'),
)

STATIC_URL = '/public/'
MEDIA_URL = '/media/'

STATIC_ROOT = env('SETTINGS_STATIC_ROOT', BASE_DIR / 'static')
MEDIA_ROOT = env('SETTINGS_MEDIA_ROOT', BASE_DIR / 'media')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

TIME_FORMAT = 'H:i'

ROOT_URLCONF = 'swat4tracker.urls'
WSGI_APPLICATION = 'swat4tracker.wsgi.application'

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
DEFAULT_FROM_EMAIL = 'noreply@swat4stats.com'

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
            'format': 'app.swat4tracker.%(name)s: [%(levelname)s] %(asctime)s - %(filename)s:%(lineno)s - %(message)s'
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
