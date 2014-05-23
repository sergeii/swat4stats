# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import os
import sys
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django import db
from django.utils import timezone

import mock
from julia import shortcuts, node
from julia.parse import QueryString
from cacheops.invalidation import invalidate_all

from tracker.models import Server
from tracker.definitions import stream_pattern_node
from tracker.signals import stream_data_received
from tracker import models


class InvalidServer(Exception):
    pass

class Command(BaseCommand):

    servers = {
        '-==MYT Team Svr==-': models.Server.objects.get_or_create(ip='81.19.209.212', port=10480)[0],
        '-==MYT Co-op Svr==-': models.Server.objects.get_or_create(ip='81.19.209.212', port=10880)[0],
        '[C=EF2929]||ESA|| [C=A90E0E]Starship! [C=ffffff]2VK=Kick!': models.Server.objects.get_or_create(ip='193.192.58.147', port=10480)[0],
    }

    def handle(self, *args, **options):
        self.count = 0

        if not args:
            raise CommandError('provide path to file')

        # invalidate redis cache
        invalidate_all()

        with open(args[0]) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.parse_line(line)


    def parse_line(self, line):
        qs = QueryString().parse(line)
        # expand querystring with either method
        qs = (QueryString.expand_dots if any('.' in key for key in qs) else QueryString.expand_array)(qs)
        try:
            data = stream_pattern_node.parse(qs)
        except node.ValueNodeError as e:
            self.stdout.write(str(e))
        else:

            try:
                models.Game.objects.get(tag=data['tag'].value)
            except ObjectDoesNotExist:
                pass
            else:
                self.stdout.write('%s exists' % data['tag'].value)
                return

            try:
                round_date = self.parse_datetime(data['timestamp'].value)
                with mock.patch.object(timezone, 'now') as mock_now:
                    mock_now.return_value = round_date
                    # fix distance
                    self.fix_distance(data)
                    # emit signal
                    stream_data_received.send(sender=None, data=data, server=self.servers[data['hostname'].value], raw=line)
            except (db.utils.IntegrityError, KeyError) as e:
                self.stdout.write(str(e))
            else:
                self.count += 1
                self.stdout.write('#%d' % self.count)
                db.reset_queries()

    def parse_datetime(self, timestamp):
        date = datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)
        if date > datetime.datetime(2014, 3, 30, 1, 0, 0, tzinfo=timezone.utc):
            date -= datetime.timedelta(seconds=3600)
        return date

    def fix_distance(self, data):
        if data.get('players', None) is None:
            return
        if data['version'].value.split('.') > ['0', '1']:
            return
        for player in data['players']:
            if player.get('weapons', None):
                for weapon in player['weapons']:
                    weapon['distance'].value *= 100
