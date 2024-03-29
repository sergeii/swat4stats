from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytz import UTC

from apps.tracker.models import Alias
from apps.tracker.tasks import update_search_vector, update_search_vector_for_model
from apps.tracker.tasks.search import SearchVectorModel
from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import AliasFactory, ProfileFactory, ServerFactory


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

    # fmt: off
    assert mccree.search == "'cassidy':2B,10C,12C,14C,16C 'cree':5C,9C 'mc':4C,8C 'mccree':1A,6C,7C 'outlaw':3B,11C,13C,15C,17C"  # noqa: E501
    assert mccree.search_updated_at == now
    # fmt: on

    # fmt: off
    assert soldier.search == "'jack':7C,11C 'jackmorrison':2B,9C,10C 'morrison':8C,12C 'solider':4C,6C 'solider76':1A,3C,5C"  # noqa: E501
    # fmt: on

    assert soldier.search_updated_at == now

    assert roadhog.search == "'roadhog':1A,2C,3C,4C,5C"
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

    assert mccree.search == "'cree':3B,7B 'mc':2B,6B 'mccree':1A,4B,5B"
    assert mccree.search_updated_at == now

    assert soldier.search == "'solider':3B,5B 'solider76':1A,2B,4B"
    assert soldier.search_updated_at == now

    assert roadhog.search == "'roadhog':1A,2B,3B,4B,5B"
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

    assert myt.search == "'myt':1A,4B,7B,10B,13B 'svr':3A,6B,9B,12B,15B 'team':2A,5B,8B,11B,14B"
    assert myt.search_updated_at == now

    # fmt: off
    assert legends.search == "'cooo':8B,21B 'cooop':4A,13B,17B 'die':3A,7B,12B,16B,20B 'legends':1A,5B,10B,14B,18B 'never':2A,6B,11B,15B,19B 'p':9B,22B"  # noqa: E501
    assert legends.search_updated_at == now
    # fmt: on

    # fmt: off
    assert sog.search == "'co':9B,14B 'pro':2A,4B,6B,11B,16B 'sog':7B,12B 'sog-team.co.uk':1A,3B,5B 'team':8B,13B 'uk':10B,15B" # noqa: E501
    # fmt: on
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
