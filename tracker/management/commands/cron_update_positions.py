# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import warnings

from django.core.management.base import BaseCommand, CommandError
from tracker import tasks


class Command(BaseCommand):
    """
    Calculate and save positions for each leaderboard withon a selected year.

    Usage:
        python manage.py cron_update_positions 2007 2008 2009
        python manage.py cron_update_positions
        python manage.py cron_update_positions -- -2 -1 0

    The management command is kept for backward compatibility.
    """
    def handle(self, *args, **kwargs):
        warnings.warn('Use of %s is deprecated. Use celery instead.' % __name__, DeprecationWarning)
        tasks.update_positions(*tuple(map(int, args)))
