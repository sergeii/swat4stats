import logging
from typing import Any

from django.db import transaction

from apps.geoip.models import ISP
from apps.tracker.models import Server, ServerStats
from apps.tracker.signals import failed_servers_detected, live_servers_detected
from apps.utils.misc import concat_it
from swat4stats.celery import Queue, app

__all__ = [
    "merge_server_stats",
    "merge_servers",
    "refresh_listed_servers",
    "unlist_failed_servers",
    "update_server_country",
    "update_server_ratings",
]

logger = logging.getLogger(__name__)


@app.task(name="refresh_listed_servers", queue=Queue.serverquery.value)
def refresh_listed_servers() -> None:
    """
    Refresh listed servers (i.e. the servers that are expected to be online)
    """
    listed_servers = list(Server.objects.listed())

    logger.debug("refreshing status for %d servers", len(listed_servers))
    status, errors = Server.objects.refresh_status(*listed_servers)

    servers_failed: dict[Server, Exception] = {}
    servers_live: dict[Server, dict[str, Any]] = {}

    for server, result in status:
        servers_live[server] = result
        logger.debug("successfully refreshed status for %s (%s)", server.address, server)

    for server, exc in errors:
        servers_failed[server] = exc
        logger.info(
            "failed to refresh status for %s (%s) due to %s: %s",
            server.address,
            server,
            type(exc),
            exc,
        )

    if servers_live:
        logger.debug("%s of %s servers are live", len(servers_live), len(status))
        live_servers_detected.send(sender=None, servers=servers_live)

    if servers_failed:
        logger.debug("%s of %s servers are failed", len(servers_failed), len(status))
        failed_servers_detected.send(sender=None, servers=servers_failed)


@app.task(name="unlist_failed_servers", queue=Queue.serverquery.value)
def unlist_failed_servers() -> None:
    """
    Unlist servers that have reached the maximum number of tolerated failures.
    """
    offline_servers = list(Server.objects.get_listed_servers_with_exceeded_failures())

    if not offline_servers:
        logger.debug("no servers with too many query failures detected")
        return

    server_ids = [obj.pk for obj in offline_servers]

    logger.info("detected %d listed servers with too many query failures", len(offline_servers))

    if updated_cnt := Server.objects.unlist_servers(*server_ids):
        logger.info("unlisted %d of %d offline servers", updated_cnt, len(offline_servers))
    else:
        logger.info("did not unlist any of %d offline servers", len(offline_servers))

    if deleted_cnt := Server.objects.delete_status(*offline_servers):
        logger.info(
            "deleted status for %d of %d offline servers", deleted_cnt, len(offline_servers)
        )
    else:
        logger.info("did not delete status for any of %d offline servers", len(offline_servers))


@app.task(time_limit=10, queue=Queue.default.value)
def update_server_country(server_id: int) -> None:
    """
    Detect and update the server's country.
    """
    obj = Server.objects.get(pk=server_id)
    isp, _ = ISP.objects.match_or_create(obj.ip)

    if not (isp and isp.country):
        logger.info("wont update country for server %s due to empty isp/country", server_id)
        return

    logger.info("updating country to %s for server %s", isp.country, server_id)
    Server.objects.filter(pk=server_id).update(country=isp.country)


@app.task(name="update_server_ratings", queue=Queue.default.value)
def update_server_ratings() -> None:
    Server.objects.update_ratings()


@app.task(queue=Queue.heavy.value)
@transaction.atomic(durable=True)
def merge_servers(main_server_id: int, merged_server_ids: list[int]) -> None:
    logger.info(
        "about to start merging servers %s into %s", concat_it(merged_server_ids), main_server_id
    )

    server_ids = [*merged_server_ids, main_server_id]
    servers = (
        Server.objects.select_for_update(no_key=True).order_by("pk").in_bulk(id_list=server_ids)
    )

    main_server = servers[main_server_id]
    merged_servers = [servers[server_id] for server_id in merged_server_ids]

    merged_servers_str = concat_it([f"{server} {server.pk}" for server in merged_servers])
    # fmt: off
    logger.info(
        "merging %d servers %s into %s (%s)",
        len(merged_server_ids), merged_servers_str, main_server, main_server_id,
    )
    # fmt: on
    Server.objects.merge_servers(main=main_server, merged=merged_servers, no_savepoint=True)

    # fmt: off
    logger.info(
        "finished merging %d servers %s into %s (%s)",
        len(merged_server_ids), merged_servers_str, main_server, main_server_id,
    )
    # fmt: on


@app.task(name="merge_server_stats", queue=Queue.heavy.value)
def merge_server_stats() -> None:
    ServerStats.objects.merge_unmerged_stats()
