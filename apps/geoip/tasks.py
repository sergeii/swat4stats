import logging

from swat4stats.celery import app
from apps.geoip.models import IP

logger = logging.getLogger(__name__)


@app.task(name='delete_expired_ips')
def delete_expired_ips():
    """
    Remove old expired IPs, so they can be renewed with fresh data.
    """
    queryset = IP.objects.expired()
    logger.info('deleting %s expired ips', queryset.count())
    queryset.delete()
