from django.core.management import call_command

from apps.geoip.factories import ISPFactory
from apps.tracker.factories import AliasFactory, ProfileFactory


def test_fill_last_seen(db, django_assert_num_queries):
    profile1 = ProfileFactory(name='Serge')
    profile2 = ProfileFactory(name=None)
    profile3 = ProfileFactory(name='Killa')
    profile4 = ProfileFactory(name='Officer')

    isp1 = ISPFactory(name='I.S.P.', country='fr')

    # denorm fields are empty, have all related fields non-empty
    alias1 = AliasFactory(profile=profile1, isp=isp1, profile_name=None, isp_name=None, isp_country=None)

    # denorm fields are empty, have all related fields empty
    alias2 = AliasFactory(profile=profile2, isp=None, profile_name=None, isp_name=None, isp_country=None)

    # denorm fields filled, overwritten by related fields
    alias3 = AliasFactory(profile=profile3, isp=isp1, profile_name='afk', isp_name='some isp', isp_country='cy')

    # denorm fields filled, zeroed by empty related fields
    alias4 = AliasFactory(profile=profile4, isp=None, profile_name='suspect', isp_name='some isp', isp_country='cy')

    with django_assert_num_queries(3):
        call_command('fill_alias_denorm')

    for p in [alias1, alias2, alias3, alias4]:
        p.refresh_from_db()

    assert alias1.profile_name == 'Serge'
    assert alias1.isp_name == 'I.S.P.'
    assert alias1.isp_country == 'fr'

    assert alias2.profile_name is None
    assert alias2.isp_name is None
    assert alias2.isp_country is None

    assert alias3.profile_name == 'Killa'
    assert alias3.isp_name == 'I.S.P.'
    assert alias3.isp_country == 'fr'

    assert alias4.profile_name == 'Officer'
    assert alias4.isp_name is None
    assert alias4.isp_country is None
