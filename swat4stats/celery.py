import os

from celery import Celery
from celery.signals import setup_logging, celeryd_init
from kombu.serialization import register

from apps.utils import xjson

from .sentry import configure_sentry_for_celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swat4stats.settings')


@setup_logging.connect
def configure_logging(sender=None, **kwargs):
    """
    Stop celery from hijacking loggers.
    https://github.com/celery/celery/issues/1867
    """
    pass


@celeryd_init.connect
def init_sentry(**_kwargs):
    configure_sentry_for_celery()


register('xjson', xjson.dumps, xjson.loads, content_type='application/x-xjson', content_encoding='utf-8')


app = Celery('swat4stats')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
