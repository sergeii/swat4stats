import logging
from typing import Any

from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings
from django_redis import get_redis_connection

from apps.tracker.models import Server

logger = logging.getLogger(__name__)

game_data_received = Signal()  # providing_args=['data', 'server', 'raw', 'request']
game_data_saved = Signal()  # providing_args=['data', 'server', 'game']
live_servers_detected = Signal()  # providing_args=['servers']
failed_servers_detected = Signal()  # providing_args=['servers']
offline_servers_detected = Signal()  # providing_args=['servers']


@receiver(post_save, sender=Server)
def queue_update_server_country(sender, instance, **kwargs):
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
@transaction.atomic
def relist_live_server(sender, servers, **kwargs):
    """
    Ensure the failure count is reset once a server is back online.
    """
    queryset = (Server.objects
                .filter(pk__in=[obj.pk for obj in servers], failures__gte=0)
                .select_for_update())
    queryset.relist()
    logger.debug('relisted %s servers', len(servers))


@receiver(failed_servers_detected)
def detect_offline_servers(sender, servers, **kwargs):
    """
    Update failure count for the failed servers.
    If the failure count value exceeds the max number of failures, unlist the server.
    """
    pks = list(map(lambda obj: obj.pk, servers))

    logger.debug('%s servers failed', len(servers))

    Server.objects.filter(pk__in=pks).update(failures=F('failures') + 1)
    offline_servers = (Server.objects
                       .filter(pk__in=pks, failures__gte=settings.TRACKER_STATUS_FAILURES))

    if offline_servers:
        logger.debug('%s servers are offline', len(offline_servers))
        offline_servers_detected.send(sender=None, servers=offline_servers)


@receiver(offline_servers_detected)
@transaction.atomic
def unlist_offline_servers(sender, servers, **kwargs):
    """Unlist servers that have been detected as offline"""
    redis = get_redis_connection()
    server_pks = [server.pk for server in servers]
    queryset = (
        Server.objects
        .filter(pk__in=server_pks)
        .select_for_update()
    )
    queryset.update(listed=False)
    redis.hdel(settings.TRACKER_SERVER_REDIS_KEY, *(server.address for server in servers))
    logger.info('Unlisted %s servers: %s', len(servers), server_pks)


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
def queue_update_profile_games(sender, game, **kwargs):
    from apps.tracker.tasks import update_profile_games
    transaction.on_commit(lambda: update_profile_games.delay(game.pk))


@receiver(game_data_received)
def queue_save_game_data(sender, data, server, **kwargs):
    """
    Attempt to create a new game in background from parsed data.
    """
    from apps.tracker.tasks import process_game_data
    transaction.on_commit(lambda: process_game_data.delay(server_id=server.pk,
                                                          data=data,
                                                          data_received_at=timezone.now()))


@receiver(game_data_received)
def log_raw_game_data(sender, raw, server, **kwargs):
    logging.getLogger('stream').info('%s: %s', server.address, raw)


@receiver(game_data_received)
def update_server_version(sender, data, server, **kwargs):
    """
    Store version of the tracker mod running on the server.
    """
    server.version = data['version']
    server.save(update_fields=['version'])
