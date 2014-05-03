# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import threading
from time import sleep

from django.core.management.base import BaseCommand, CommandError

from tracker import models, utils, config

logger = logging.getLogger(__name__)

# the semaphore serves for enforcing number of concurrent connections
semaphore = threading.Semaphore(config.MAX_STATUS_CONNECTIONS)


class QueryThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.server = kwargs.pop('server')
        super(QueryThread, self).__init__(*args, **kwargs)

    def run(self):
        semaphore.acquire()
        self.server.query()
        semaphore.release()


class Command(BaseCommand):

    def handle(self, limit, interval, *args, **options):
        """
        Query the enabled server every `interval` seconds untill the `limit` is over.

        Usage:
            python manage.py cron_query_servers 60 5
        """
        limit = eval(limit)
        interval = eval(interval)
        total = 0

        while total < limit:
            self.query()
            total += interval
            sleep(interval)

    def query(self):
        """Query the active servers that have been marked to be listed."""
        for server in models.Server.objects.listed():
            thread = QueryThread(server=server)
            thread.start()