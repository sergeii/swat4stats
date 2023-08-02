import os

from django.core.wsgi import get_wsgi_application

from .sentry import configure_sentry_for_wsgi

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swat4stats.settings")

configure_sentry_for_wsgi()

application = get_wsgi_application()
