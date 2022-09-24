from django.core.management.base import BaseCommand

from apps.tracker.models import Server


class Command(BaseCommand):

    def handle(self, *args, **options):
        qs = Server.objects.listed().filter()

        qs.refresh_status()
        result = Server.objects.with_status()

        self.stdout.write('available %s' % qs.count())
        self.stdout.write('with status %s' % len(result))
