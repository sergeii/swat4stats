# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os

from django.conf import settings
import celery
import raven
from celery.signals import setup_logging
from raven.contrib.celery import register_signal, register_logger_signal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4tracker.settings')


@setup_logging.connect
def configure_logging(sender=None, **kwargs):
    """
    Stop celery from hijacking loggers.
    https://github.com/celery/celery/issues/1867
    """
    pass


class Celery(celery.Celery):

    def on_configure(self):
        if 'raven.contrib.django.raven_compat' in settings.INSTALLED_APPS:
            client = raven.Client(settings.RAVEN_CONFIG['dsn'])
            # register a custom filter to filter out duplicate logs
            register_logger_signal(client)
            # hook into the Celery error handler
            register_signal(client)


app = Celery('swat4tracker')
app.config_from_object(settings)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
