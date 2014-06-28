# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os

from celery import Celery

from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4tracker.settings')

app = Celery('swat4tracker')

app.config_from_object(settings)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
