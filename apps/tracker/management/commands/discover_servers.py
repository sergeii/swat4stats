from django.core.management.base import BaseCommand

from apps.tracker.models import Server


class Command(BaseCommand):

    def handle(self, *args, **options):
        Server.objects.discover_published_servers()
