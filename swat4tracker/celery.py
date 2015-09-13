# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os
import logging

from django.conf import settings
import celery


class Celery(celery.Celery):

    def on_configure(self):
        raven_config = getattr(settings, 'RAVEN_CONFIG', None)

        if not raven_config:
            return

        import raven
        from raven.contrib.celery import register_signal, register_logger_signal

        client = raven.Client(dsn=raven_config['dsn'])
        register_logger_signal(client, loglevel=logging.WARNING)
        register_signal(client)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4tracker.settings')
app = Celery('swat4tracker')

app.config_from_object(settings)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
