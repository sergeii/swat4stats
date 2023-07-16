from apps.geoip.factories import ISPFactory
from apps.geoip.models import ISP
from apps.tracker.factories import ProfileFactory, AliasFactory
from apps.tracker.models import Profile, Alias


def test_denorm_alias_profile_name(db):
    profile = ProfileFactory(name='Solider76')
    second_profile = ProfileFactory(name='Junkrat')
    foreign_profile = ProfileFactory(name='Roadhog')

    # alias is created, profile_name is set to the name of profile
    alias = AliasFactory(profile=profile, profile_name=None)
    alias.refresh_from_db()
    assert alias.profile_name == 'Solider76'

    other_alias = AliasFactory(profile=profile)
    other_alias.refresh_from_db()
    assert other_alias.profile_name == 'Solider76'

    foreign_alias = AliasFactory(profile=foreign_profile, profile_name=None)
    foreign_alias.refresh_from_db()
    assert foreign_alias.profile_name == 'Roadhog'

    # profile name is changed, alias profile_name is also changed for all referenced aliases
    Profile.objects.filter(pk=profile.pk).update(name='Mercy')
    alias.refresh_from_db()
    assert alias.profile_name == 'Mercy'

    other_alias.refresh_from_db()
    assert other_alias.profile_name == 'Mercy'

    # profile reference is changed, profile_name is updated
    Alias.objects.filter(pk=alias.pk).update(profile=second_profile)
    alias.refresh_from_db()
    assert alias.profile_name == 'Junkrat'

    # because profile was not changed for other_alias, profile_name is not updated
    other_alias.refresh_from_db()
    assert other_alias.profile_name == 'Mercy'

    # other players' aliases are not affected
    foreign_alias.refresh_from_db()
    assert foreign_alias.profile_name == 'Roadhog'


def test_denorm_alias_isp_name(db):
    isp = ISPFactory(name='Comcast', country='us')
    new_isp = ISPFactory(name='Frontier', country='us')
    foreign_isp = ISPFactory(name='Canal Plus', country='fr')

    # alias is created, isp_name and isp_country are set to the name and country of the isp
    alias = AliasFactory(isp=isp, isp_name=None, isp_country=None)
    alias.refresh_from_db()
    assert alias.isp_name == 'Comcast'
    assert alias.isp_country == 'us'

    other_alias = AliasFactory(isp=isp)
    other_alias.refresh_from_db()
    assert other_alias.isp_name == 'Comcast'
    assert other_alias.isp_country == 'us'

    foreign_alias = AliasFactory(isp=foreign_isp, isp_name=None, isp_country=None)
    foreign_alias.refresh_from_db()
    assert foreign_alias.isp_name == 'Canal Plus'

    # isp name is changed, alias isp_name is also changed for all referenced aliases
    ISP.objects.filter(pk=isp.pk).update(name='AT&T')
    alias.refresh_from_db()
    other_alias.refresh_from_db()

    assert alias.isp_name == 'AT&T'
    assert alias.isp_country == 'us'
    assert other_alias.isp_name == 'AT&T'
    assert other_alias.isp_country == 'us'

    # isp country is changed, alias isp_country is also changed for all referenced aliases
    ISP.objects.filter(pk=isp.pk).update(country='ca')
    alias.refresh_from_db()
    other_alias.refresh_from_db()

    assert alias.isp_name == 'AT&T'
    assert alias.isp_country == 'ca'
    assert other_alias.isp_name == 'AT&T'
    assert other_alias.isp_country == 'ca'

    # name and country are changed, alias isp_name and isp_country are also changed for all referenced aliases
    ISP.objects.filter(pk=isp.pk).update(name='Verizon', country='mx')
    alias.refresh_from_db()
    other_alias.refresh_from_db()

    assert alias.isp_name == 'Verizon'
    assert alias.isp_country == 'mx'
    assert other_alias.isp_name == 'Verizon'
    assert other_alias.isp_country == 'mx'

    # isp reference is changed, isp_name and isp_country are updated
    Alias.objects.filter(pk=alias.pk).update(isp=new_isp)
    alias.refresh_from_db()
    assert alias.isp_name == 'Frontier'
    assert alias.isp_country == 'us'

    # isp is removed, isp_name and isp_country are set to None
    Alias.objects.filter(pk=alias.pk).update(isp=None)
    alias.refresh_from_db()
    assert alias.isp_name is None
    assert alias.isp_country is None

    # the other alias is not affected by the change
    other_alias.refresh_from_db()
    assert other_alias.isp_name == 'Verizon'
    assert other_alias.isp_country == 'mx'

    # other aliases are not affected by the changes
    foreign_alias.refresh_from_db()
    assert foreign_alias.isp_name == 'Canal Plus'
    assert foreign_alias.isp_country == 'fr'
