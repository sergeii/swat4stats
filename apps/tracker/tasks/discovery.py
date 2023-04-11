import logging

from apps.tracker.models import Server
from swat4stats.celery import app


__all__ = [
    'discover_published_servers',
    'discover_good_query_ports',
]

logger = logging.getLogger(__name__)


@app.task(name='discover_published_servers')
def discover_published_servers():
    """Discover new swat 4 servers using various sources"""
    Server.objects.discover_published_servers()


@app.task(name='discover_good_query_ports')
def discover_good_query_ports():
    Server.objects.discover_good_query_ports()
