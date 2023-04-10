import logging

from django.conf import settings

from swat4stats.celery import app
from apps.tracker.models import Server
from apps.tracker.signals import live_servers_detected, failed_servers_detected
from apps.geoip.models import ISP
from apps.utils.misc import iterate_queryset


__all__ = [
    'refresh_listed_servers',
    'refresh_servers_chunk',
    'update_server_country',
]

logger = logging.getLogger(__name__)


@app.task(name='refresh_listed_servers', queue='serverquery')
def refresh_listed_servers():
    """
    Refresh listed servers (i.e. the servers that are expected to be online)
    """
    chunk_size = settings.TRACKER_STATUS_CONCURRENCY
    queryset = Server.objects.listed().only('pk')
    for chunk in iterate_queryset(queryset, fields=['pk'], chunk_size=chunk_size):
        logger.debug('queue refresh_servers_chunk for %s servers', len(chunk))
        refresh_servers_chunk.delay(*(obj['pk'] for obj in chunk))


@app.task(expires=5, time_limit=5, queue='serverquery')
def refresh_servers_chunk(*pks):
    """
    Query status for specified servers.
    """
    servers_failed = {}
    servers_live = {}

    logger.debug('refreshing %s servers', len(pks))
    status, errors = Server.objects.filter(pk__in=pks).refresh_status()

    for server, result in status:
        servers_live[server] = result
        logger.debug('successfuly refreshed status for %s (%s)', server.address, server)

    for server, exc in errors:
        servers_failed[server] = exc
        logger.info('failed to refresh status for %s (%s) due to %s: %s',
                    server.address, server, type(exc), exc)

    if servers_live:
        logger.debug('%s of %s servers are live', len(servers_live), len(status))
        live_servers_detected.send(sender=None, servers=servers_live)

    if servers_failed:
        logger.debug('%s of %s servers are failed', len(servers_failed), len(status))
        failed_servers_detected.send(sender=None, servers=servers_failed)


@app.task(time_limit=10)
def update_server_country(server_id):
    """
    Detect and update the server's country.
    """
    obj = Server.objects.get(pk=server_id)
    isp, _ = ISP.objects.match_or_create(obj.ip)

    if not (isp and isp.country):
        logger.info('wont update country for server %s due to empty isp/country', server_id)
        return

    logger.info('updating country to %s for server %s', isp.country, server_id)
    Server.objects.filter(pk=server_id).update(country=isp.country)
