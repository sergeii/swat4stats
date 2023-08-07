from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytz import UTC

from apps.tracker.factories import ProfileFactory, AliasFactory
from apps.tracker.tasks import denorm_profile_names
from apps.utils.test import freeze_timezone_now


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC))
@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (1000, 7),
        (2, 21),
        (4, 14),
    ],
)
def test_denorm_profile_names(
    now_mock,
    django_assert_num_queries,
    chunk_size,
    expected_queries,
):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    profile = ProfileFactory(
        name="McCree",
        alias_updated_at=yesterday,
        names_updated_at=week_ago,
        names=["McCree", "Cassidy", "Outlaw"],
    )
    AliasFactory(profile=profile, name="McCree")
    AliasFactory(profile=profile, name="Cassidy")

    other_profile = ProfileFactory(
        name="Solider76", alias_updated_at=yesterday, names_updated_at=None, names=[]
    )
    AliasFactory(profile=other_profile, name="Solider76")
    AliasFactory(profile=other_profile, name="JackMorrison")
    AliasFactory(profile=other_profile, name="JackMorrison")

    single_name_profile = ProfileFactory(
        name="Roadhog", alias_updated_at=yesterday, names_updated_at=None, names=None
    )
    AliasFactory(profile=single_name_profile, name="Roadhog")

    no_alias_profile = ProfileFactory(name="Widowmaker", alias_updated_at=None)
    no_alias_profile_with_names = ProfileFactory(
        name="Mei", alias_updated_at=yesterday, names=["Snowball"]
    )

    no_name_profile = ProfileFactory(name=None, alias_updated_at=yesterday)
    AliasFactory(profile=no_name_profile, name="Reaper")
    AliasFactory(profile=no_name_profile, name="Reyes")

    already_updated_profile = ProfileFactory(
        name="Mercy",
        alias_updated_at=week_ago,
        names_updated_at=yesterday,
        names=["Angela", "DrZiegler"],
    )
    AliasFactory(profile=already_updated_profile, name="Mercy")
    AliasFactory(profile=already_updated_profile, name="Angela")

    # for some reason this profile has aliases but no alias_updated_at set
    broken_profile_with_aliases = ProfileFactory(
        name="Genji", alias_updated_at=None, names_updated_at=None, names=None
    )
    AliasFactory(profile=broken_profile_with_aliases, name="Genji")
    AliasFactory(profile=broken_profile_with_aliases, name="Sparrow")

    with django_assert_num_queries(expected_queries):
        denorm_profile_names.delay(chunk_size=chunk_size)

    for p in [
        profile,
        other_profile,
        single_name_profile,
        no_alias_profile,
        no_name_profile,
        no_alias_profile_with_names,
        already_updated_profile,
    ]:
        p.refresh_from_db()

    # names were updated for profile because alias_updated_at > names_updated_at
    assert profile.names == ["Cassidy"]
    assert profile.names_updated_at == now
    assert profile.alias_updated_at == yesterday

    assert no_alias_profile_with_names.names == []
    assert no_alias_profile_with_names.names_updated_at == now
    assert no_alias_profile_with_names.alias_updated_at == yesterday

    # names were updated for profile because names_updated_at is None
    assert other_profile.names == ["JackMorrison"]
    assert other_profile.names_updated_at == now
    assert other_profile.alias_updated_at == yesterday

    assert single_name_profile.names == []
    assert single_name_profile.names_updated_at == now
    assert single_name_profile.alias_updated_at == yesterday

    # profile without alias_updated_at should not be updated
    assert no_alias_profile.names is None
    assert no_alias_profile.names_updated_at is None
    assert no_alias_profile.alias_updated_at is None

    # names were not updated for already updated profile (alias_updated_at < names_updated_at)
    assert already_updated_profile.names == ["Angela", "DrZiegler"]
    assert already_updated_profile.names_updated_at == yesterday
    assert already_updated_profile.alias_updated_at == week_ago

    # names were not updated for broken profile (alias_updated_at is None)
    assert broken_profile_with_aliases.names is None
    assert broken_profile_with_aliases.names_updated_at is None
    assert broken_profile_with_aliases.alias_updated_at is None

    # because all profiles are up to date, no new update queries should be executed
    now_mock.return_value = now + timedelta(days=1)
    with django_assert_num_queries(3):
        denorm_profile_names.delay(chunk_size=chunk_size)

    for p in [profile, other_profile, no_alias_profile_with_names, single_name_profile]:
        p.refresh_from_db()
        assert p.names_updated_at == now
