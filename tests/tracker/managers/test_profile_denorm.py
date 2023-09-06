from datetime import datetime

import pytest
from pytz import UTC

from apps.tracker.models import Alias, Profile
from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import AliasFactory, ProfileFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_denorm_profile_alias_names_on_update():
    profile = ProfileFactory(name="McCree")
    AliasFactory(profile=profile, name="McCree")

    other_profile = ProfileFactory(name="Solider76")
    AliasFactory(profile=other_profile, name="Solider76")

    single_name_profile = ProfileFactory(name="Roadhog")
    AliasFactory(profile=single_name_profile, name="Roadhog")

    no_alias_profile = ProfileFactory(name="Widowmaker")

    no_name_profile = ProfileFactory(name=None)
    AliasFactory(profile=no_name_profile, name="Reaper")
    AliasFactory(profile=no_name_profile, name="Reyes")

    Profile.objects.denorm_alias_names(
        profile.pk,
        other_profile.pk,
        single_name_profile.pk,
        no_alias_profile.pk,
        no_name_profile.pk,
    )

    no_alias_profile.refresh_from_db()
    assert no_alias_profile.names == []

    no_name_profile.refresh_from_db()
    assert no_name_profile.names == ["Reaper", "Reyes"]

    for p in [profile, other_profile, single_name_profile]:
        p.refresh_from_db()
        assert p.names == []

    AliasFactory(profile=profile, name="Cassidy")
    Profile.objects.denorm_alias_names(profile.pk)
    profile.refresh_from_db()
    assert profile.names == ["Cassidy"]

    # other profiles are not affected
    for p in [other_profile, single_name_profile]:
        p.refresh_from_db()
        assert p.names == []
    no_alias_profile.refresh_from_db()
    assert no_alias_profile.names == []

    # add more aliases, names are updated
    AliasFactory(profile=other_profile, name="Jack")
    AliasFactory(profile=other_profile, name="Morrison")
    AliasFactory(profile=other_profile, name="Morrison")
    Profile.objects.denorm_alias_names(other_profile.pk)
    other_profile.refresh_from_db()
    assert other_profile.names == ["Jack", "Morrison"]


@pytest.mark.django_db(databases=["default", "replica"])
def test_denorm_profile_alias_names_on_delete():
    profile = ProfileFactory(name="McCree")
    AliasFactory(profile=profile, name="McCree")
    AliasFactory(profile=profile, name="Cassidy")

    other_profile = ProfileFactory(name="Solider76")
    AliasFactory(profile=other_profile, name="Solider76")
    AliasFactory(profile=other_profile, name="Jack")
    AliasFactory(profile=other_profile, name="Morrison")

    no_name_profile = ProfileFactory(name=None)
    AliasFactory(profile=no_name_profile, name="Reaper")
    AliasFactory(profile=no_name_profile, name="Reyes")

    # delete all aliases, names are emptied
    Alias.objects.filter(profile=profile).delete()
    Profile.objects.denorm_alias_names(profile.pk)
    profile.refresh_from_db()
    assert profile.names == []

    # delete some aliases, names are updated
    Alias.objects.filter(profile=other_profile, name__in=["Soldier76", "Morrison"]).delete()
    Profile.objects.denorm_alias_names(other_profile.pk)
    other_profile.refresh_from_db()
    assert other_profile.names == ["Jack"]

    # delete all aliases for profile with no name, names are updated
    Alias.objects.filter(profile=no_name_profile, name="Reyes").delete()
    Profile.objects.denorm_alias_names(no_name_profile.pk)
    no_name_profile.refresh_from_db()
    assert no_name_profile.names == ["Reaper"]


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC))
def test_update_search_vector_for_many_profiles(now_mock, django_assert_num_queries):
    mccree = ProfileFactory(name="McCree", names=["Cassidy", "Cowboy"])
    solider76 = ProfileFactory(name="Solider76", names=["Jack", "Morrison"])
    reaper = ProfileFactory(name=None, names=["Reaper", "Gabriel", "Reyes"])
    mercy = ProfileFactory(name="Mercy", names=[])
    mei = ProfileFactory(name="Mei", names=None)
    unknown = ProfileFactory(name=None, names=None)

    with django_assert_num_queries(4):
        Profile.objects.update_search_vector(
            mccree.pk, solider76.pk, reaper.pk, mercy.pk, mei.pk, unknown.pk
        )

    for p in [mccree, solider76, reaper, mercy, mei, unknown]:
        p.refresh_from_db()
        assert p.search is not None
        assert p.search_updated_at == datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC)


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC))
@pytest.mark.parametrize(
    "name, names, tsv",
    [
        (
            "McCree",
            ["Cassidy", "Cowboy"],
            "'cassidy':2B,10C,12C,14C,16C 'cowboy':3B,11C,13C,15C,17C 'cree':5C,9C 'mc':4C,8C 'mccree':1A,6C,7C",  # noqa: E501
        ),
        (
            "Winston123",
            ["Winston", "Churchill"],
            "'churchill':3B,9C,11C,13C,15C 'winston':2B,5C,7C,8C,10C,12C,14C 'winston123':1A,4C,6C",
        ),
        (None, ["Mercy", "Angela"], "'angela':2B,4C,6C,8C,10C 'mercy':1B,3C,5C,7C,9C"),
        ("Mercy", [], "'mercy':1A,2C,3C,4C,5C"),
        ("Mercy", None, "'mercy':1A,2C,3C,4C,5C"),
        (None, None, ""),
    ],
)
def test_update_search_vector_for_one_profile(
    now_mock, django_assert_num_queries, name, names, tsv
):
    profile = ProfileFactory(name=name, names=names)

    with django_assert_num_queries(4):
        Profile.objects.update_search_vector(profile.pk)

    profile.refresh_from_db()
    assert profile.search == tsv
    assert profile.search_updated_at == datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC)
