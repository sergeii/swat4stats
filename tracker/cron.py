# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import threading

import cronjobs

from . import models

logger = logging.getLogger(__name__)


@cronjobs.register
def query_servers():
    """Query the active servers."""
    for server in models.Server.objects.enabled():
        # no status set
        if not server.status:
            status = models.ServerStatus.create(server=server)
        else:
            status = server.status
        # query the server
        # the model will be saved as well as the response is cached
        if not status.query_status():
            logger.error('failed to query %s' % server)