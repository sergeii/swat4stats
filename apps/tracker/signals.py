import logging
from typing import Any

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from apps.tracker.models import Game, Server

logger = logging.getLogger(__name__)

game_data_received = Signal()  # providing_args=['data', 'server', 'request']
game_data_saved = Signal()  # providing_args=['data', 'server', 'game']
live_servers_detected = Signal()  # providing_args=['servers']
failed_servers_detected = Signal()  # providing_args=['servers']


@receiver(post_save, sender=Server)
@transaction.atomic(savepoint=False)
def delay_update_server_country(
    sender: Any,  # noqa: ARG001
    instance: Server,
    **_: Any,
) -> None:
    from apps.tracker.tasks import update_server_country

    transaction.on_commit(lambda: update_server_country.delay(instance.pk))


@receiver(live_servers_detected)
def update_live_servers_hostnames(
    sender: Any,  # noqa: ARG001
    servers: dict[Server, dict],
    **_: Any,
) -> None:
    new_hostnames_for_servers = []

    for server, status in servers.items():
        # don't update the hostname if it's the same
        if server.hostname == status["hostname"]:
            continue

        new_hostnames_for_servers.append((server, status["hostname"]))
        logger.info(
            "current hostname '%s' for %s is different from '%s'",
            server.hostname,
            server.pk,
            status["hostname"],
        )

    if not new_hostnames_for_servers:
        logger.debug("no hostname changes needed for %d live servers", len(servers))
        return

    Server.objects.update_hostnames(*new_hostnames_for_servers)


@receiver(live_servers_detected)
def reset_server_failure_count(
    sender: Any,  # noqa: ARG001
    servers: list[Server],
    **_: Any,
) -> None:
    server_ids = [server.pk for server in servers]

    if updated_cnt := Server.objects.reset_query_failures(*server_ids, listed=True):
        logger.debug("reset failures for %d of %d live servers", updated_cnt, len(servers))


@receiver(failed_servers_detected)
def inc_failures_for_failed_servers(
    sender: Any,  # noqa: ARG001
    servers: list[Server],
    **_: Any,
) -> None:
    failed_server_ids = [server.pk for server in servers]

    if updated_cnt := Server.objects.increment_query_failures(*failed_server_ids):
        logger.info(
            "updated failures for %d of %d failed servers", updated_cnt, len(failed_server_ids)
        )
    else:
        logger.info("did not update failures for any of %d failed servers", len(failed_server_ids))


@receiver(game_data_saved)
def relist_streaming_server(
    sender: Any,  # noqa: ARG001
    data: dict[str, Any],  # noqa: ARG001
    server: Server,
    game: Game,  # noqa: ARG001
    **_: Any,
) -> None:
    if server.listed:
        logger.debug("streaming server %s (%s) is already listed", server, server.pk)
        return

    logger.info("streaming server %s (%s) is not listed", server, server.pk)

    if Server.objects.relist_servers(server.pk):
        logger.info("relisted streaming server %s (%s)", server, server.pk)
    else:
        logger.info("did not relist streaming server %s (%s)", server, server.pk)


@receiver(game_data_saved)
def change_hostname_for_streaming_server(
    sender: Any,  # noqa: ARG001
    data: dict[str, Any],
    server: Server,
    game: Game,  # noqa: ARG001
    **_: Any,
) -> None:
    server_hostname = server.hostname
    # check whether the hostname has changed for this server
    if not (data["hostname"] and data["hostname"] != server_hostname):
        # fmt: off
        logger.debug(
            "current hostname '%s' for %s has not changed ('%s')",
            server_hostname, server.pk, data["hostname"],
        )
        # fmt: on
        return

    # fmt: off
    logger.info(
        "current hostname '%s' for %s is different from '%s'",
        server_hostname, server.pk, data["hostname"],
    )
    # fmt: on

    if Server.objects.update_hostnames((server, data["hostname"])):
        # fmt: off
        logger.info(
            "updated hostname for streaming server %s to '%s from '%s'",
            server.pk, data["hostname"], server_hostname,
        )
        # fmt: on
    else:
        logger.info(
            "did not update hostname for streaming server %s to '%s'", server.pk, data["hostname"]
        )


@receiver(game_data_saved)
@transaction.atomic(savepoint=False)
def delay_game_related_stats_tasks(sender: Any, game: Game, **kwargs: Any) -> None:  # noqa: ARG001
    from apps.tracker.tasks import update_map_games, update_profile_games, update_server_games

    transaction.on_commit(lambda: update_profile_games.delay(game.pk))
    transaction.on_commit(lambda: update_server_games.delay(game.pk))
    transaction.on_commit(lambda: update_map_games.delay(game.pk))
