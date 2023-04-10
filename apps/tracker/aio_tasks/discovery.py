import logging
from typing import Any
from collections.abc import Callable

import aiohttp
from django.conf import settings

from apps.tracker.utils import aio


logger = logging.getLogger(__name__)


class ServerDiscoveryTask(aio.Task):

    class DiscoveryException(Exception):
        pass

    def __init__(self, *, url: str, parser: Callable, **kwargs: Any) -> None:
        self.url = url
        self.parser = parser
        super().__init__(**kwargs)

    @aio.with_timeout(settings.TRACKER_SERVER_DISCOVERY_TIMEOUT)
    async def start(self) -> list[tuple[str, str]]:
        logger.info('requesting %s', self.url)
        headers = {
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(self.url, headers=headers) as response:
                logger.debug('connected to %s: %s', self.url, response.status)

                if not 200 <= response.status <= 299:
                    raise self.DiscoveryException('invalid response status %s' % response.status)

                response_body = await response.read()
                logger.debug('received %s bytes from %s', len(response_body), self.url)

                return self.parser(response_body)
