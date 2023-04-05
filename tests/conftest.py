import logging

from django.db import transaction
import pytest


@pytest.fixture(autouse=True)
def _configure_default_storage(settings):
    settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


@pytest.fixture(autouse=True)
def _disable_debug(settings):
    settings.DEBUG = False


@pytest.fixture(scope='session', autouse=True)
def _disable_logging():
    logging.disable()


@pytest.fixture(scope='session', autouse=True)
def _patch_on_commit_hook():
    old_on_commit = transaction.on_commit
    transaction.on_commit = lambda func, *args, **kwargs: func()
    yield
    transaction.on_commit = old_on_commit


@pytest.fixture(autouse=True)
def caches():
    from django.conf import settings
    from django.core.cache import caches

    yield caches

    for alias in settings.CACHES:
        caches[alias]._cache.get_client().flushdb()
