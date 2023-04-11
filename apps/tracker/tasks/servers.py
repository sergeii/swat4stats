import logging
from typing import Any

from swat4stats.celery import app
from apps.tracker.models import Server
from apps.tracker.signals import live_servers_detected, failed_servers_detected
from apps.geoip.models import ISP


__all__ = [
    'refresh_listed_servers',
    'update_server_country',
]

logger = logging.getLogger(__name__)


@app.task(name='refresh_listed_servers', queue='serverquery')
def refresh_listed_servers() -> None:
    """
    Refresh listed servers (i.e. the servers that are expected to be online)
    """
    queryset = Server.objects.listed()

    logger.debug('refreshing status for %s servers', queryset.count())
    status, errors = queryset.refresh_status()

    servers_failed: dict[Server, Exception] = {}
    servers_live: dict[Server, dict[str, Any]] = {}

    for server, result in status:
        servers_live[server] = result
        logger.debug('successfully refreshed status for %s (%s)', server.address, server)

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
def update_server_country(server_id: int) -> None:
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
