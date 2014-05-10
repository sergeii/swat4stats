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

# list of available servers
servers_listed = set()
# list of servers that have responded to a query
servers_alive = set()


class QueryThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.server = kwargs.pop('server')
        super(QueryThread, self).__init__(*args, **kwargs)

    def run(self):
        semaphore.acquire()

        try:
            self.server.query()
        except:
            pass
        else:
            # the server is okay
            servers_alive.add(self.server.pk)

        semaphore.release()


class Command(BaseCommand):

    def handle(self, limit, interval, *args, **options):
        """
        Query the enabled server every `interval` seconds untill the `limit` is over.

        Usage:
            python manage.py cron_query_servers 60 5
        """
        threads = []
        limit = eval(limit)
        interval = eval(interval)
        total = 0

        while total < limit:
            # clear the thread list
            threads = []

            for server in models.Server.objects.listed():
                servers_listed.add(server.pk)
                threads.append(QueryThread(server=server))
            # query the servers
            [thread.start() for thread in threads]
            
            total += interval
            sleep(interval)

        # only wait for the last group of threads
        [thread.join() for thread in threads]

        pks = servers_listed-servers_alive
        # unlist the servers that have never responded to a query
        models.Server.objects.filter(pk__in=pks).update(listed=False)
        logger.warning('Unlisted %s servers' % len(pks))