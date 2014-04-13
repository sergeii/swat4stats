# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.core.management.base import BaseCommand, CommandError
from django import db

from tracker import models


class Command(BaseCommand):

    def handle(self, *args, **options):
        models.Profile.TIME_POPULAR = 3600*24*365*10

        for profile in models.Profile.objects.all():
            profile.date_played = profile.fetch_last_seen()
            profile.update_popular(save=True)
            self.stdout.write('Updated %s' % profile.name)
            db.reset_queries()
