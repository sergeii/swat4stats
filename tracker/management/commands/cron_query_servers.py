# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import warnings

from django.core.management.base import BaseCommand, CommandError
from tracker import tasks


class Command(BaseCommand):

    def handle(self, limit, interval, *args, **options):
        """
        Query the enabled server every `interval` seconds untill the `limit` is over.

        Usage:
            python manage.py cron_query_servers 60 5

        The management command is kept for backward compatibility.
        """
        warnings.warn('Use of %s is deprecated. Use celery instead.' % __name__, DeprecationWarning)
        tasks.query_servers(time_delta=eval(limit), interval=eval(interval))
