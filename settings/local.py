from .common import BASE_DIR, INSTALLED_APPS, MIDDLEWARE


DEBUG = True

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)

INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
) + MIDDLEWARE

STATIC_ROOT = BASE_DIR / 'static'
MEDIA_ROOT = BASE_DIR / 'media'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEBUG_TOOLBAR_PATCH_SETTINGS = False

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
