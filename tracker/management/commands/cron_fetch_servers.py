import re
import random
import logging
import threading

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache as redis

from tracker import models, utils, config

logger = logging.getLogger(__name__)

lock = threading.Lock()


class FetchListThread(threading.Thread):
    timeout = 1
    # a list of user agents to pick from
    user_agents = (
        r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36',
        r'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
        r'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:28.0) Gecko/20100101 Firefox/28.0',
        r'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
        r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:28.0) Gecko/20100101 Firefox/28.0',
        r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.74.9 (KHTML, like Gecko) Version/7.0.2 Safari/537.74.9',
        r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
        r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36',
        r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14',
    )

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        self.pattern = kwargs.pop('pattern')
        super(FetchListThread, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        try:
            response = requests.get(self.url, headers=headers, timeout=self.timeout)
        except Exception as e:
            logger.critical('failed to fetch %s (%s, %s)' % (self.url, type(e), e))
        else:
            # fetch and parse data
            data = response.text
            for match in self.pattern.finditer(data):
                ip, port = match.group('addr'), match.group('port')
                # lock threads from concurrent access
                with lock:
                    try:
                        obj = models.Server.objects.get(ip=ip, port=port)
                    except ObjectDoesNotExist:
                        try:
                            # make sure the server will be queried automatically, hence listed=True
                            models.Server.objects.create_server(ip, port, enabled=True, listed=True)
                            logger.info('added %s:%s from %s' % (ip, port, self.url))
                        except Exception as e:
                            logger.error('failed to add %s:%s (%s, %s)' % (ip, port, type(e), e))
                    else:
                        # relist the server
                        if obj.enabled and not obj.listed and not obj.port_gs1:
                            obj.listed = True
                            obj.count_failure = 0
                            obj.save(update_fields=['listed', 'count_failure'])
                            logger.debug('relisted %s' % obj)
                        else:
                            logger.debug('skipped %s' % obj)


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Fetch the pages listed in `urls` class variable.
        """
        for url, pattern in config.SERVER_URLS:
            thread = FetchListThread(url=url, pattern=pattern)
            thread.start()
