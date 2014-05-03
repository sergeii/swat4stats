# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import logging
from optparse import make_option

import six
from django.core.management.base import BaseCommand, CommandError
from django import db

from tracker import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--cache',
            action='store_true',
            dest='cache',
            default=False,
        ),
    )

    def handle(self, *args, **options):
        years = list(map(int, args))
        for year in years:
            self.empty_ranking(year)

        for year in years:
            start, end = models.Rank.get_period_for_year(year)
            qs = (models.Profile.objects
                .popular()
                .filter(
                    alias__player__game__date_finished__gte=start, 
                    alias__player__game__date_finished__lte=end
                )
                .distinct('pk')
            )

            for profile in qs:
                print('Checking %s, %s' % (profile.name, profile.pk))
                aggregated = profile.aggregate_mode_stats(models.Profile.SET_STATS_ALL, start, end)
                models.Rank.objects.store_many(aggregated, year, profile)

        if options['cache']:
            for year in years:
                models.Rank.objects.rank(year)

    @staticmethod
    def empty_ranking(year):
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                'DELETE FROM {table} WHERE year=%s'.format(table=models.Rank._meta.db_table), 
                [year]
            )
        finally:
            cursor.close()