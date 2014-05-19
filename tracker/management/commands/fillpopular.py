# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from optparse import make_option

from mock import patch
from django.core.management.base import BaseCommand, CommandError
from django import db
from django.utils import timezone

from tracker import models


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--no-extreme',
            action='store_true',
            dest='skip_extreme',
            default=True,
        ),
    )

    def handle(self, *args, **options):
        now_real = timezone.now
        # set custom TIME_POPULAR
        if args:
            seconds = eval(args[0])
            try:
                assert isinstance(seconds, int)
            except AssertionError:
                raise CommandError('%s cannot be evaluated as an integer' % args[0])
            else:
                models.Profile.TIME_POPULAR = seconds

        for profile in models.Profile.objects.select_related('game_first', 'game_last', 'loadout').order_by('pk'):
            if not options['skip_extreme']:
                try:
                    game_first, game_last = self.get_extreme_games(profile)
                except models.Game.DoesNotExist:
                    pass
                else:
                    profile.game_first = game_first
                    profile.game_last = game_last
            # only update if last game entry is present
            if profile.game_last.date_finished:
                # set last played game's date as the current time
                with patch.object(timezone, 'now') as mock:
                    mock.return_value = profile.game_last.date_finished
                    profile.update_popular()
                profile.save()
                self.stdout.write('Updated %s' % profile.name)
            else:
                self.stdout.write('Failed to update %s' % profile.name)
            db.reset_queries()

    @staticmethod
    def get_extreme_games(profile):
        qs = models.Game.objects.filter(player__alias__profile=profile)
        return (qs.order_by('date_finished')[:1].get(), qs.order_by('-date_finished')[:1].get())
