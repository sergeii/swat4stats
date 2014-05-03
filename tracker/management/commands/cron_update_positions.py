# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
import six

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from tracker import models


class Command(BaseCommand):
    """
    Calculate and save positions for each leaderboard withon a selected year.

    Usage:
        python manage.py cron_update_positions 2007 2008 2009
        python manage.py cron_update_positions
        python manage.py cron_update_positions -- -2 -1 0
    """
    def handle(self, *args, **kwargs):
        years = []
        current_year = timezone.now().year

        for arg in args:
            try:
                if arg[0] in ('0', '-', '+'):
                    # difference to the current year
                    years.append(int(arg) + current_year)
                else:
                    # year as is
                    years.append(int(arg))
            except:
                raise CommandError('%s is not a valid year' % arg)

        # use the current year as fallback
        if not years:
            years.append(current_year)

        for year in years:
            self.stdout.write('updating positions for %s' % year)
            models.Rank.objects.rank(year)
