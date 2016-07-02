# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.core.management.base import BaseCommand
from tracker import tasks


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('limit')
        parser.add_argument('interval')

    def handle(self, limit, interval, *args, **options):
        """
        Query the enabled server every `interval` seconds untill the `limit` is over.

        Usage:
            python manage.py cron_query_servers 60 5

        The management command is kept for backward compatibility.
        """
        tasks.query_listed_servers(time_delta=eval(limit), interval=eval(interval))
