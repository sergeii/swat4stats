import os

import celery
import raven
from celery.signals import setup_logging
from kombu.serialization import register
from raven.contrib.celery import register_signal, register_logger_signal

from apps.utils import xjson

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')


@setup_logging.connect
def configure_logging(sender=None, **kwargs):
    """
    Stop celery from hijacking loggers.
    https://github.com/celery/celery/issues/1867
    """
    pass


class Celery(celery.Celery):

    def on_configure(self):
        from django.conf import settings
        if 'raven.contrib.django.raven_compat' in settings.INSTALLED_APPS:
            client = raven.Client(**settings.RAVEN_CONFIG)
            # register a custom filter to filter out duplicate logs
            register_logger_signal(client)
            # hook into the Celery error handler
            register_signal(client)


register('xjson', xjson.dumps, xjson.loads, content_type='application/x-xjson', content_encoding='utf-8')


app = Celery('swat4stats')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
