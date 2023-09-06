from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from unittest import mock

import pytest
from pytz import UTC

from apps.tracker.models import Alias
from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import AliasFactory


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC))
def test_update_search_vector_for_many_aliases(
    now_mock: mock.Mock,
    django_assert_num_queries: Callable[[int], AbstractContextManager],
) -> None:
    mccree = AliasFactory(name="McCree")
    solider76 = AliasFactory(name="Solider76")
    mercy = AliasFactory(name="Mercy")
    unknown = AliasFactory(name="")

    with django_assert_num_queries(4):
        Alias.objects.update_search_vector(mccree.pk, solider76.pk, mercy.pk, unknown.pk)

    for a in [mccree, solider76, mercy, unknown]:
        a.refresh_from_db()
        assert a.search is not None
        assert a.search_updated_at == datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC)


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC))
@pytest.mark.parametrize(
    "name, tsv",
    [
        (
            "McCree",
            "'cree':3B,7B 'mc':2B,6B 'mccree':1A,4B,5B",
        ),
        (
            "Winston123",
            "'winston':3B,5B 'winston123':1A,2B,4B",
        ),
        (
            "WinstonChurchill123",
            "'churchill':7B 'churchill123':3B 'winston':2B,6B 'winstonchurchill':4B 'winstonchurchill123':1A,5B",  # noqa: E501
        ),
        ("Mercy", "'mercy':1A,2B,3B,4B,5B"),
        ("", ""),
    ],
)
def test_update_search_vector_for_one_alias(
    now_mock: mock.Mock,
    django_assert_num_queries: Callable[[int], AbstractContextManager],
    name: str,
    tsv: str,
) -> None:
    alias = AliasFactory(name=name)

    with django_assert_num_queries(4):
        Alias.objects.update_search_vector(alias.pk)

    alias.refresh_from_db()
    assert alias.search == tsv
    assert alias.search_updated_at == datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC)
