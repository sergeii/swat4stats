import logging
from typing import Any
from collections.abc import Callable

import aiohttp
from django.conf import settings

from apps.tracker.utils import aio


logger = logging.getLogger(__name__)


class ServerDiscoveryError(Exception):
    ...


class ServerDiscoveryTask(aio.Task):
    def __init__(self, *, url: str, parser: Callable, **kwargs: Any) -> None:
        self.url = url
        self.parser = parser
        super().__init__(**kwargs)

    async def start(self) -> list[tuple[str, str]]:
        logger.info("requesting %s", self.url)
        headers = {
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        new_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=True),
            timeout=aiohttp.ClientTimeout(total=settings.TRACKER_SERVER_DISCOVERY_HTTP_TIMEOUT),
        )
        async with new_session as session, session.get(self.url, headers=headers) as response:
            logger.debug("connected to %s: %s", self.url, response.status)

            if not 200 <= response.status <= 299:
                raise ServerDiscoveryError("invalid response status %s" % response.status)

            response_body = await response.read()
            logger.debug("received %s bytes from %s", len(response_body), self.url)

            return self.parser(response_body)
