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
    Update profile "popular" fields for the players that have played time seconds ago.

    Usage:
        python manage.py cron_update_ranks '60*60*24'
    """
    def handle(self, time, *args, **kwargs):
        min_date = timezone.now() - datetime.timedelta(seconds=eval(time))
        queryset = (models.Profile.objects
            .popular()
            .select_related('game_last')
            .filter(game_last__date_finished__gte=min_date)
        )
        with transaction.atomic():
            for profile in queryset:
                # aggregate stats relative to the last game's date
                year = profile.last_seen.year
                period = models.Rank.get_period_for_year(year)
                with transaction.atomic():
                    # aggregate stats for the specified period
                    stats = profile.aggregate_mode_stats(models.Profile.SET_STATS_ALL, *period)
                    models.Rank.objects.store_many(stats, year, profile)