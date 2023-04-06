import logging

from django.core.management.base import BaseCommand
from django.db.models import Q, F, Model


logger = logging.getLogger(__name__)


def fill_status_port(server_model: type[Model]) -> int:
    updated = (server_model.objects
               .filter(Q(status_port__isnull=True) | Q(status_port=0))
               .update(status_port=F('port') + 1))
    return updated


class Command(BaseCommand):

    def handle(self, *args, **options):
        from apps.tracker.models import Server

        console = logging.StreamHandler()
        logger.addHandler(console)

        updated = fill_status_port(Server)
        logger.info('filled status port for %s servers', updated)
