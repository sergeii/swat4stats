# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os

from django.conf import settings
import celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4tracker.settings')
app = celery.Celery('swat4tracker')

app.config_from_object(settings)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
