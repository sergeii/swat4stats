import logging

from django.core.management.base import BaseCommand
from django.db.models import Q, F

from apps.tracker.models import Server


logger = logging.getLogger(__name__)


def fill_status_port():
    updated = (Server.objects
               .filter(Q(status_port__isnull=True) | Q(status_port=0))
               .update(status_port=F('port') + 1))
    logger.info('filled status port for %s servers', updated)


class Command(BaseCommand):

    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_status_port()
