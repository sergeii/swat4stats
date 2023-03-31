import os

import sentry_sdk


def configure_sentry():
    if sentry_dsn := os.environ.get('SETTINGS_SENTRY_DSN'):
        traces_sample_rate = os.environ.get('SETTINGS_SENTRY_SAMPLE_RATE')
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=float(traces_sample_rate) if traces_sample_rate else 0.0,
        )
