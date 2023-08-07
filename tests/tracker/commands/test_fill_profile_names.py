import pytest
from django.core.management import call_command

from apps.tracker.factories import AliasFactory, ProfileFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_profile_names(django_assert_num_queries):
    profile = ProfileFactory(name="McCree")
    AliasFactory(profile=profile, name="McCree")
    AliasFactory(profile=profile, name="Cassidy")

    other_profile = ProfileFactory(name="Solider76")
    AliasFactory(profile=other_profile, name="Solider76")
    AliasFactory(profile=other_profile, name="JackMorrison")
    AliasFactory(profile=other_profile, name="JackMorrison")

    single_name_profile = ProfileFactory(name="Roadhog")
    AliasFactory(profile=single_name_profile, name="Roadhog")

    no_alias_profile = ProfileFactory(name="Widowmaker")

    no_name_profile = ProfileFactory(name=None)
    AliasFactory(profile=no_name_profile, name="Reaper")
    AliasFactory(profile=no_name_profile, name="Reyes")

    with django_assert_num_queries(7):
        call_command("fill_profile_names")

    for p in [profile, other_profile, single_name_profile, no_alias_profile, no_name_profile]:
        p.refresh_from_db()

    assert profile.names == ["Cassidy"]
    assert other_profile.names == ["JackMorrison"]
    assert single_name_profile.names == []
    assert no_alias_profile.names == []
    assert no_name_profile.names == ["Reaper", "Reyes"]
