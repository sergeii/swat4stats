from datetime import datetime

import pytest
from pytz import UTC

from apps.tracker.factories import AliasFactory
from apps.tracker.models import Alias
from apps.utils.test import freeze_timezone_now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC))
def test_update_search_vector_for_many_aliases(now_mock, django_assert_num_queries):
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
            "'cree':3B 'mc':2B 'mccree':1A",
        ),
        (
            "Winston123",
            "'winston':2B 'winston123':1A",
        ),
        (
            "WinstonChurchill123",
            "'churchill':3B 'winston':2B 'winstonchurchill123':1A",
        ),
        ("Mercy", "'mercy':1A,2B"),
        ("", ""),
    ],
)
def test_update_search_vector_for_one_alias(now_mock, django_assert_num_queries, name, tsv):
    alias = AliasFactory(name=name)

    with django_assert_num_queries(4):
        Alias.objects.update_search_vector(alias.pk)

    alias.refresh_from_db()
    assert alias.search == tsv
    assert alias.search_updated_at == datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC)
