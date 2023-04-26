import logging
from typing import Any

from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.db import transaction
from django.db.models import F
from django.conf import settings
from django_redis import get_redis_connection

from apps.tracker.models import Server, Game

logger = logging.getLogger(__name__)

game_data_received = Signal()  # providing_args=['data', 'server', 'request']
game_data_saved = Signal()  # providing_args=['data', 'server', 'game']
live_servers_detected = Signal()  # providing_args=['servers']
failed_servers_detected = Signal()  # providing_args=['servers']
offline_servers_detected = Signal()  # providing_args=['servers']


@receiver(post_save, sender=Server)
@transaction.atomic(savepoint=False)
def queue_update_server_country(sender: Any, instance: Server, **kwargs: Any) -> None:
    from apps.tracker.tasks import update_server_country
    transaction.on_commit(lambda: update_server_country.delay(instance.pk))


@receiver(live_servers_detected)
def update_live_servers_hostnames(sender: Any, servers: dict[Server, dict], **kwargs: Any) -> None:
    """
    Attempt to detect hostname change for a server.
    If positive, set the new hostname.
    """
    servers_to_update = []

    for server, status in servers.items():
        if server.hostname != status['hostname']:
            logger.info('updating %s hostname from "%s" to "%s"',
                        server.pk, server.hostname, status['hostname'])
            server.hostname = status['hostname']
            servers_to_update.append(server)

    if servers_to_update:
        logger.info('updating hostname for %s servers', len(servers_to_update))
        Server.objects.bulk_update(servers_to_update, ['hostname'])


@receiver(live_servers_detected)
def reset_server_failure_count(sender: Any, servers: list[Server], **kwargs: Any) -> None:
    """
    Ensure the failure count is reset once a server is back online.
    """
    queryset = (Server.objects
                .filter(pk__in=(obj.pk for obj in servers)))

    if updated := queryset.reset_failures():
        logger.debug('reset failures for %d of %d live servers', updated, len(servers))


@receiver(failed_servers_detected)
def detect_offline_servers(sender: Any, servers: list[Server], **kwargs: Any) -> None:
    """
    Update failure count for the failed servers.
    If the failure count value exceeds the max number of failures, unlist the server.
    """
    pks = [server.pk for server in servers]
    Server.objects.filter(pk__in=pks).update(failures=F('failures') + 1)

    offline_servers_qs = (Server.objects
                          .filter(pk__in=pks, failures__gte=settings.TRACKER_STATUS_TOLERATED_FAILURES))
    if offline_servers := offline_servers_qs:
        logger.debug('%d of %d failed servers are offline', len(offline_servers), len(servers))
        offline_servers_detected.send(sender=None, servers=offline_servers)


@receiver(offline_servers_detected)
def unlist_offline_servers(sender: Any, servers: list[Server], **kwargs: Any) -> None:
    """Unlist servers that have been detected as offline"""
    redis = get_redis_connection()
    redis.hdel(settings.TRACKER_STATUS_REDIS_KEY, *(server.address for server in servers))

    queryset = Server.objects.filter(pk__in=(obj.pk for obj in servers), listed=True)
    if updated := queryset.update(listed=False):
        logger.info('unlisted %d of %d offline servers', updated, len(servers))


@receiver(game_data_saved)
def update_streaming_server(sender, data, server, game, **kwargs):
    update_fields = []

    if not server.listed:
        server.listed = True
        server.failures = 0
        update_fields.extend(['listed', 'failures'])
        logger.info('relisting a streaming server %s (%s)', server, server.pk)

    if data['hostname'] and data['hostname'] != server.hostname:
        logger.info('updating server %s hostname from %s to data hostname %s',
                    server.pk, server.hostname, data['hostname'])
        server.hostname = data['hostname']
        update_fields.append('hostname')

    if update_fields:
        server.save(update_fields=update_fields)


@receiver(game_data_saved)
@transaction.atomic(savepoint=False)
def queue_update_profile_games(sender: Any, game: Game, **kwargs: Any) -> None:
    from apps.tracker.tasks import update_profile_games
    transaction.on_commit(lambda: update_profile_games.delay(game.pk))
