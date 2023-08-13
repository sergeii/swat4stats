import argparse
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.views.decorators.csrf import csrf_exempt

from apps.tracker.views import DataStreamView


class Command(BaseCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Path to file with urlencoded games")

    def handle(self, *args: Any, **options: Any) -> None:
        path = options["path"]
        factory = RequestFactory()
        with Path.open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                request = factory.post(
                    "/stream/",
                    data=line,
                    content_type="application/x-www-form-urlencoded",
                    REAL_REMOTE_ADDR="127.0.0.1",
                )
                csrf_exempt(DataStreamView.as_view())(request)
