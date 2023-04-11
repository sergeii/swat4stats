import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration


def configure_sentry_for_wsgi() -> None:
    if not (sentry_dsn := os.environ.get('SETTINGS_SENTRY_API_DSN')):
        return
    traces_sample_rate = os.environ.get('SETTINGS_SENTRY_API_SAMPLE_RATE')
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=float(traces_sample_rate) if traces_sample_rate else 0.0,
    )


def configure_sentry_for_celery() -> None:
    if not (sentry_dsn := os.environ.get('SETTINGS_SENTRY_CELERY_DSN')):
        return
    traces_sample_rate = os.environ.get('SETTINGS_SENTRY_CELERY_SAMPLE_RATE')
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=float(traces_sample_rate) if traces_sample_rate else 0.0,
        integrations=[
            CeleryIntegration(),
        ],
    )
