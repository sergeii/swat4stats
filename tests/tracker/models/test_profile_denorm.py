from apps.tracker.factories import ProfileFactory, AliasFactory
from apps.tracker.models import Alias


def test_denorm_profile_alias_names_on_create(db):
    profile = ProfileFactory(name='McCree')
    AliasFactory(profile=profile, name='McCree')

    other_profile = ProfileFactory(name='Solider76')
    AliasFactory(profile=other_profile, name='Solider76')

    single_name_profile = ProfileFactory(name='Roadhog')
    AliasFactory(profile=single_name_profile, name='Roadhog')

    no_alias_profile = ProfileFactory(name='Widowmaker')

    no_name_profile = ProfileFactory(name=None)
    AliasFactory(profile=no_name_profile, name='Reaper')
    AliasFactory(profile=no_name_profile, name='Reyes')

    no_alias_profile.refresh_from_db()
    assert no_alias_profile.names is None

    no_name_profile.refresh_from_db()
    assert no_name_profile.names == ['Reaper', 'Reyes']

    for p in [profile, other_profile, single_name_profile]:
        p.refresh_from_db()
        assert p.names == []

    AliasFactory(profile=profile, name='Cassidy')
    profile.refresh_from_db()
    assert profile.names == ['Cassidy']

    # other profiles are not affected
    for p in [other_profile, single_name_profile]:
        p.refresh_from_db()
        assert p.names == []
    no_alias_profile.refresh_from_db()
    assert no_alias_profile.names is None

    # add more aliases, names are updated
    AliasFactory(profile=other_profile, name='Jack')
    AliasFactory(profile=other_profile, name='Morrison')
    AliasFactory(profile=other_profile, name='Morrison')
    other_profile.refresh_from_db()
    assert other_profile.names == ['Jack', 'Morrison']


def test_denorm_profile_alias_names_on_delete(db):
    profile = ProfileFactory(name='McCree')
    AliasFactory(profile=profile, name='McCree')
    AliasFactory(profile=profile, name='Cassidy')

    other_profile = ProfileFactory(name='Solider76')
    AliasFactory(profile=other_profile, name='Solider76')
    AliasFactory(profile=other_profile, name='Jack')
    AliasFactory(profile=other_profile, name='Morrison')

    no_name_profile = ProfileFactory(name=None)
    AliasFactory(profile=no_name_profile, name='Reaper')
    AliasFactory(profile=no_name_profile, name='Reyes')

    # delete all aliases, names are emptied
    Alias.objects.filter(profile=profile).delete()
    profile.refresh_from_db()
    assert profile.names == []

    # delete some aliases, names are updated
    Alias.objects.filter(profile=other_profile, name__in=['Soldier76', 'Morrison']).delete()
    other_profile.refresh_from_db()
    assert other_profile.names == ['Jack']

    # delete all aliases for profile with no name, names are updated
    Alias.objects.filter(profile=no_name_profile, name='Reyes').delete()
    no_name_profile.refresh_from_db()
    assert no_name_profile.names == ['Reaper']
