from typing import Any

from django.core.management.base import BaseCommand

from apps.tracker.models import Server


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        listed_servers = Server.objects.listed()

        Server.objects.refresh_status(*listed_servers)
        servers_with_status = Server.objects.with_status()

        self.stdout.write(f"available {len(listed_servers.count())}")
        self.stdout.write(f"with status {len(servers_with_status)}")
