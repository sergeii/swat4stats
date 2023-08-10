from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytz import UTC

from apps.tracker.factories import ProfileFactory, AliasFactory, ServerFactory
from apps.tracker.models import Alias
from apps.tracker.tasks import update_search_vector, update_search_vector_for_model
from apps.tracker.tasks.search import SearchVectorModel
from apps.utils.test import freeze_timezone_now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC))
def test_update_search_vector_smoke(now_mock):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    soldier = ProfileFactory(
        name="Solider76", names_updated_at=yesterday, search_updated_at=None, names=["JackMorrison"]
    )
    mccree = AliasFactory(name="McCree", updated_at=yesterday, search_updated_at=week_ago)
    myt = ServerFactory(
        hostname_clean="-==MYT Team Svr==-",
        hostname_updated_at=yesterday,
        search_updated_at=week_ago,
    )

    update_search_vector.delay()

    for obj in [soldier, mccree, myt]:
        obj.refresh_from_db()

    assert soldier.search_updated_at == now
    assert mccree.search_updated_at == now
    assert myt.search_updated_at == now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC))
@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (1000, 5),
        (4, 5),
        (2, 10),
    ],
)
def test_update_search_vector_for_profiles(
    now_mock,
    django_assert_num_queries,
    chunk_size,
    expected_queries,
):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    mccree = ProfileFactory(
        name="McCree",
        names_updated_at=yesterday,
        search_updated_at=week_ago,
        names=["Cassidy", "Outlaw"],
    )

    soldier = ProfileFactory(
        name="Solider76", names_updated_at=yesterday, search_updated_at=None, names=["JackMorrison"]
    )

    roadhog = ProfileFactory(
        name="Roadhog", names_updated_at=yesterday, search_updated_at=week_ago, names=[]
    )

    already_updated_profile = ProfileFactory(
        name="Reaper", names_updated_at=week_ago, search_updated_at=yesterday, names=["Reyes"]
    )

    never_updated_profile = ProfileFactory(
        name="Widowmaker", names_updated_at=None, search_updated_at=None, names=[]
    )

    with django_assert_num_queries(expected_queries):
        update_search_vector_for_model.delay(SearchVectorModel.profile, chunk_size=chunk_size)

    for profile in [mccree, soldier, roadhog, already_updated_profile, never_updated_profile]:
        profile.refresh_from_db()

    assert mccree.search == "'cassidy':2B,6C 'cree':5C 'mc':4C 'mccree':1A 'outlaw':3B,7C"
    assert mccree.search_updated_at == now

    assert soldier.search == "'jack':4C 'jackmorrison':2B 'morrison':5C 'solider':3C 'solider76':1A"
    assert soldier.search_updated_at == now

    assert roadhog.search == "'roadhog':1A,2C"
    assert roadhog.search_updated_at == now

    assert already_updated_profile.search is None
    assert already_updated_profile.search_updated_at == yesterday

    assert never_updated_profile.search is None
    assert never_updated_profile.search_updated_at is None

    # because all profiles were updated, the task should not update any more profiles
    now_mock.return_value = now + timedelta(days=1)
    with django_assert_num_queries(3):
        update_search_vector_for_model.delay(SearchVectorModel.profile, chunk_size=chunk_size)

    for profile in [mccree, soldier, roadhog]:
        profile.refresh_from_db()
        assert profile.search_updated_at == now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 4, 18, 13, 1, 45, tzinfo=UTC))
@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (1000, 5),
        (4, 5),
        (2, 10),
    ],
)
def test_update_search_vector_for_aliases(
    now_mock,
    django_assert_num_queries,
    chunk_size,
    expected_queries,
):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    mccree = AliasFactory(name="McCree", updated_at=yesterday, search_updated_at=week_ago)
    soldier = AliasFactory(name="Solider76", updated_at=yesterday, search_updated_at=None)
    roadhog = AliasFactory(name="Roadhog", updated_at=yesterday, search_updated_at=week_ago)
    for alias in [mccree, soldier, roadhog]:
        Alias.objects.filter(pk=alias.pk).update(updated_at=yesterday)

    already_updated_alias = AliasFactory(name="Reaper", search_updated_at=yesterday)
    Alias.objects.filter(pk=already_updated_alias.pk).update(updated_at=week_ago)

    with django_assert_num_queries(expected_queries):
        update_search_vector_for_model.delay(SearchVectorModel.alias, chunk_size=chunk_size)

    for alias in [mccree, soldier, roadhog, already_updated_alias]:
        alias.refresh_from_db()

    assert mccree.search == "'cree':3B 'mc':2B 'mccree':1A"
    assert mccree.search_updated_at == now

    assert soldier.search == "'solider':2B 'solider76':1A"
    assert soldier.search_updated_at == now

    assert roadhog.search == "'roadhog':1A,2B"
    assert roadhog.search_updated_at == now

    assert already_updated_alias.search is None
    assert already_updated_alias.search_updated_at == yesterday

    # because all aliases were updated, the task should not update any more aliases
    now_mock.return_value = now + timedelta(days=1)
    with django_assert_num_queries(3):
        update_search_vector_for_model.delay(SearchVectorModel.alias, chunk_size=chunk_size)

    for alias in [mccree, soldier, roadhog]:
        alias.refresh_from_db()
        assert alias.search_updated_at == now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 4, 18, 13, 1, 45, tzinfo=UTC))
@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (1000, 5),
        (4, 5),
        (2, 10),
    ],
)
def test_update_search_vector_for_servers(
    now_mock,
    django_assert_num_queries,
    chunk_size,
    expected_queries,
):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    myt = ServerFactory(
        hostname_clean="-==MYT Team Svr==-",
        hostname_updated_at=yesterday,
        search_updated_at=week_ago,
    )
    legends = ServerFactory(
        hostname_clean="Legends Never Die coooP =)",
        hostname_updated_at=yesterday,
        search_updated_at=None,
    )
    sog = ServerFactory(
        hostname_clean="Sog-team.co.uk Pro!",
        hostname_updated_at=yesterday,
        search_updated_at=week_ago,
    )

    already_updated_server = ServerFactory(
        hostname_clean="Swat4 Server", hostname_updated_at=week_ago, search_updated_at=yesterday
    )
    never_updated_server = ServerFactory(
        hostname_clean="Another Server", hostname_updated_at=None, search_updated_at=None
    )

    with django_assert_num_queries(expected_queries):
        update_search_vector_for_model.delay(SearchVectorModel.server, chunk_size=chunk_size)

    for server in [myt, legends, sog]:
        server.refresh_from_db()

    assert myt.search == "'myt':1A,4B 'svr':3A,6B 'team':2A,5B"
    assert myt.search_updated_at == now

    assert legends.search == "'cooo':8B 'cooop':4A 'die':3A,7B 'legends':1A,5B 'never':2A,6B 'p':9B"
    assert legends.search_updated_at == now

    assert sog.search == "'pro':2A,4B 'sog-team.co.uk':1A,3B"
    assert sog.search_updated_at == now

    assert already_updated_server.search is None
    assert already_updated_server.search_updated_at == yesterday

    assert never_updated_server.search is None
    assert never_updated_server.search_updated_at is None

    now_mock.return_value = now + timedelta(days=1)
    with django_assert_num_queries(3):
        update_search_vector_for_model.delay(SearchVectorModel.server, chunk_size=chunk_size)

    for server in [myt, legends, sog]:
        server.refresh_from_db()
        assert server.search_updated_at == now
