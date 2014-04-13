# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import logging
import six
from optparse import make_option

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
        for year in map(int, args):
            models.Rank.objects.raw(
                'DELETE FROM %s WHERE year = %s', 
                [models.Rank._meta.db_table, year]
            )
            start, end = models.Rank.get_period_for_year(year)
            for profile in models.Profile.objects.popular():
                self.stdout.write('Checking %s' % profile.name)
                for category, points in six.iteritems(profile.aggregate_mode_stats(models.Profile.SET_STATS_ALL, start, end)):
                    models.Rank.objects.store(category, year, profile, points)
                    db.reset_queries()

            if options['cache']:
                models.Rank.objects.rank(year)