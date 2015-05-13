# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import re
import random
import logging
import threading
import datetime
import time
import six
import requests

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from swat4tracker import celery_app as app
from tracker import models, utils, config
from tracker.signals import live_servers_detected, dead_servers_detected


logger = logging.getLogger(__name__)


class ServerQueryThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.server = kwargs.pop('server')
        self.live = kwargs.pop('live')  # online servers set
        self.semaphore = kwargs.pop('semaphore')
        super(ServerQueryThread, self).__init__(*args, **kwargs)

    def run(self):
        self.semaphore.acquire()
        try:
            self.server.query()
        except:
            pass
        else:
            # keep track of alive servers
            self.live.add(self.server)
        finally:
            self.semaphore.release()


@app.task(bind=True, ignore_result=True, max_retries=1, default_retry_delay=60)
def fetch_server_list(self, url, pattern):
    """
    Fetch a url ``url`` and parse the response contents using an uncompiled pattern ``pattern``.

    A compiled pattern must yield MatchObj the following named groups: ip, port.
    """

    timeout = 2

    headers = {
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except Exception as exc:
        logger.debug('failed to fetch %s (%s, %s)' % (url, type(exc), exc))
        raise self.retry(exc=exc)

    # compile the pattern
    pattern = re.compile(pattern, flags=re.M)

    for match in pattern.finditer(response.text):
        try:
            obj, created = models.Server.objects.get_or_create(
                ip=match.group('addr'), 
                port=match.group('port'),
                defaults={'enabled': True, 'listed': True}
            )
        except Exception as e:
            logger.debug('failed to add %s:%s (%s, %s)' 
                % (match.group('addr'), match.group('port'), type(e), e)
            )
        else:
            # relist an existing server
            if not created and obj.enabled and not obj.listed:
                obj.listed = True
                obj.save(update_fields=['listed'])
                logger.debug('relisted %s' % obj)

            if created:
                logger.debug('added %s:%s from %s' % (match.group('addr'), match.group('port'), url))


@app.task(ignore_result=True)
def update_server_list():
    """
    Fetch the URLs defined in config.SERVER_URLS 
    then attempt to parse the result for ip:port pairs.
    """
    for url, pattern in config.SERVER_LIST_URLS:
        fetch_server_list.apply_async(kwargs=locals())


@app.task(ignore_result=True, expires=5)
def query_listed_servers(time_delta, interval):
    """
    Attempt to query listed servers every ``interval`` for a total of ``time``.

    Args:
        time_delta - execution time (seconds/timedelta obj)
        interval - time between query cycles (seconds/timedelta obj)
    """
    threads = []
    # list of available servers
    servers_listed = set()
    # list of servers that have responded to a query
    servers_live = set()
    # enforce max number of concurrently running threads
    semaphore = threading.Semaphore(config.MAX_STATUS_CONNECTIONS)

    interval = utils.force_timedelta(interval).seconds
    # calculate the time the task must be stopped at
    stop_time = time.time() + utils.force_timedelta(time_delta).seconds
    # cache queryset
    servers = models.Server.objects.listed()

    while time.time() < stop_time:
        for server in servers:
            # keep track of servers being queried
            servers_listed.add(server)
            thread = ServerQueryThread(server=server, semaphore=semaphore, live=servers_live)
            threads.append(thread)
            # queue the thread
            thread.start()
        
        # sleep for a while
        time.sleep(interval)

    # block untill all threads finished
    [thread.join() for thread in threads]

    # servers that have replied at least once
    live_servers_detected.send(sender=None, servers=servers_live)
    # servers that have never replied by the end of the task
    dead_servers_detected.send(sender=None, servers=servers_listed-servers_live)


@app.task(ignore_result=True)
def update_popular(time_delta):
    """
    Update the profile popular fields such as name, country, loadout, etc
    that belong to players who have played just now or ``time_delta`` ago.

    Args:
        time_delta - time in past relative to the current time (seconds/timedelta obj)
    """
    min_date = timezone.now() - utils.force_timedelta(time_delta)

    queryset = (
        models.Profile.objects
        .select_for_update()
        .select_related('game_last')
        .filter(game_last__date_finished__gte=min_date)
    )
    
    with transaction.atomic():
        # update the popular fields
        for profile in queryset:
            profile.update_popular()
            profile.save()


@app.task(ignore_result=True)
def update_ranks(time_delta):
    """
    Update Rank entries that belong to players who have played just now or ``time_delta`` ago.

    Args:
        time_delta - time in past relative to the current time (seconds/timedelta obj)
    """
    min_date = timezone.now() - utils.force_timedelta(time_delta)

    queryset = (
        models.Profile.objects
        .popular()
        .select_related('game_last')
        .filter(game_last__date_finished__gte=min_date)
    )

    for profile in queryset:
        # aggregate stats relative to the last game's date
        year = profile.last_seen.year
        period = models.Rank.get_period_for_year(year)

        with transaction.atomic():
            # aggregate stats for the specified period
            stats = profile.aggregate_mode_stats(models.Profile.SET_STATS_ALL, *period)
            models.Rank.objects.store_many(stats, year, profile)


@app.task(ignore_result=True)
def update_positions(*args):
    """
    Rank up year specific leaderboards.

    Args:
        *args - years
        A zero or a negative value is considered a relative year to the current year
        Suppose 2014 is the current year, then 0 is 2014, -1 is 2013 and so on
    """
    years = []
    current_year = timezone.now().year

    for arg in args:
        # relative to the current year (0, -1, -2)
        if arg <= 0:
            years.append(arg + current_year)
        # year as is (2013, 2014, 2015)
        else:
            years.append(arg)

    # use the current year as fallback
    if not years:
        years.append(current_year)

    # rank up all leaderboard entries for every listed year
    for year in years:
        models.Rank.objects.rank(year)


@app.task(ignore_result=True)
def update_server_country(pk):
    """
    Detect and update the server's country.
    """
    obj = models.Server.objects.get(pk=pk)
    isp, created = models.ISP.objects.match_or_create(obj.ip)
    try:
        if not isp.country:
            raise AssertionError
    # country is either empty or the isp is None
    except (AssertionError, AttributeError):
        pass
    else:
        models.Server.objects.filter(pk=pk).update(country=isp.country)
