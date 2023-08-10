import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.tracker.models import Server
from apps.utils.misc import iterate_list

logger = logging.getLogger(__name__)


def fill_clean_hostnames() -> None:
    servers_with_ids = list(
        Server.objects.using("replica")
        .filter(~(Q(hostname__isnull=True) | Q(hostname="")), Q(hostname_clean__isnull=True))
        .values_list("pk", flat=True)
    )
    for server_ids in iterate_list(servers_with_ids, size=1000):
        servers_to_update = Server.objects.filter(pk__in=server_ids)
        hostname_updates = [(server, server.hostname) for server in servers_to_update]
        Server.objects.update_hostnames(*hostname_updates)


class Command(BaseCommand):
    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_clean_hostnames()
