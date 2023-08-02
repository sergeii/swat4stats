import asyncio
from pprint import pformat

from django.core.management.base import BaseCommand

from apps.tracker.aio_tasks.serverquery import ServerStatusTask


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("ip:port", help="Server status address")

    def handle(self, *args, **options):
        def callback(_, result):
            self.stdout.write(pformat(result))

        ip, port = options["ip:port"].split(":")
        task = ServerStatusTask(callback=callback, ip=ip, status_port=int(port))

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(task)
        finally:
            loop.close()
