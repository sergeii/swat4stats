import logging

from apps.geoip.models import IP
from swat4stats.celery import app

logger = logging.getLogger(__name__)


@app.task(name="delete_expired_ips")
def delete_expired_ips() -> None:
    """
    Remove old expired IPs, so they can be renewed with fresh ones.
    """
    deleted, _ = IP.objects.expired().delete()
    if deleted:
        logger.info("pruned %d expired ips", deleted)
    else:
        logger.info("no expired ips to prune")
