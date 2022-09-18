from django.db import transaction
import pytest


@pytest.fixture(scope='session', autouse=True)
def patch_on_commit_hook():
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
