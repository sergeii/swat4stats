import logging

from apps.tracker.models import Server
from swat4stats.celery import app


__all__ = [
    'discover_servers',
    'discover_extra_query_ports',
]

logger = logging.getLogger(__name__)


@app.task(name='discover_servers')
def discover_servers():
    """Discover new swat 4 servers using various sources"""
    Server.objects.discover_servers()


@app.task(name='discover_extra_query_ports')
def discover_extra_query_ports():
    Server.objects.discover_query_ports()
