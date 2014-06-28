# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import warnings

from django.core.management.base import BaseCommand, CommandError
from tracker import tasks


class Command(BaseCommand):
    """
    Update profile "popular" fields for the players that have played time seconds ago.

    Usage:
        python manage.py cron_update_ranks '60*60*24'

    The management command is kept for backward compatibility.
    """
    def handle(self, time, *args, **kwargs):
        warnings.warn('Use of %s is deprecated. Use celery instead.' % __name__, DeprecationWarning)
        tasks.update_popular(time_delta=eval(time))
