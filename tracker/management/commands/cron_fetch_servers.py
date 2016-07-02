# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.core.management.base import BaseCommand
from tracker import tasks


class Command(BaseCommand):
    """
    Fetch urls defined in tracker.config.SERVER_URLS and parse contents for ip:port pairs.

    Usage:
        python manage.py cron_fetch_servers

    The management command is kept for backward compatibility.
    """

    def handle(self, *args, **options):
        tasks.update_server_list()
