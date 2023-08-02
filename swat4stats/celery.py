import os
from enum import StrEnum, auto
from typing import Any

from celery import Celery
from celery.signals import setup_logging, celeryd_init

from .sentry import configure_sentry_for_celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swat4stats.settings")


class Queue(StrEnum):
    default = auto()
    serverquery = auto()
    heavy = auto()


@setup_logging.connect
def configure_logging(sender: Any | None = None, **kwargs: Any) -> None:
    """
    Stop celery from hijacking loggers.
    https://github.com/celery/celery/issues/1867
    """


@celeryd_init.connect
def init_sentry(**kwargs: Any) -> None:
    configure_sentry_for_celery()


app = Celery("swat4stats")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
