import os

from django.core.wsgi import get_wsgi_application

from .sentry import configure_sentry


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4tracker.settings')

configure_sentry()
application = get_wsgi_application()
