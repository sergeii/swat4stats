from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.utils import timezone

from apps.geoip.factories import ISPFactory
from apps.geoip.models import ISP, IP
from apps.tracker.factories import (ServerFactory, GameFactory,
                                    PlayerFactory, ProfileFactory,
                                    AliasFactory)
from apps.tracker.models import Profile, Alias


def test_match_will_match_against_known_pair_of_name_ip(db):
    profile = ProfileFactory()
    PlayerFactory(alias__profile=profile, alias__name='Serge', alias__isp=None, ip='127.0.0.1')

    obj = Profile.objects.match(name='Serge', player__ip='127.0.0.1')
    assert obj == profile


def test_match_smart_with_no_args_wont_match_anything(db):
    PlayerFactory(alias__name='Serge', alias__isp=None, ip='127.0.0.1')
    PlayerFactory(alias__name='foo', alias__isp__ip='127.0.0.0/16', ip='127.0.0.1')

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart()


def test_match_smart_prefers_name_ip_to_name_isp(db):
    isp1 = ISPFactory(ip='127.0.0.0/16')
    isp2 = ISPFactory(ip='192.168.0.0/16')

    profile1, profile2 = ProfileFactory.create_batch(2)
    PlayerFactory(alias__profile=profile1, alias__name='Serge', alias__isp=isp1, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile2, alias__name='Serge', alias__isp=isp2, ip='192.168.1.10')

    assert Profile.objects.match_smart(name='Serge', ip='127.0.0.1', isp=isp2).pk == profile1.pk
    assert Profile.objects.match_smart(name='Serge', ip='192.168.1.10', isp=isp1).pk == profile2.pk


def test_match_smart_null_isp_does_not_match_against_existing_null_isp(db):
    profile = ProfileFactory()
    PlayerFactory(alias__profile=profile, alias__name='Serge', alias__isp=None, ip='127.0.0.1')

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Serge', isp=None)

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.2')

    assert Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.1') == profile


def test_match_smart_empty_isp_does_not_match_against_existing_non_null_isp(db):
    profile = ProfileFactory()
    PlayerFactory(alias__profile=profile, alias__name='Serge', alias__isp=ISPFactory(), ip='127.0.0.1')

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Serge', isp=None)

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.2')

    assert Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.1') == profile


def test_match_smart_will_not_match_other_profiles_with_null_isp(db):
    profile1, profile2 = ProfileFactory.create_batch(2)
    PlayerFactory(alias__profile=profile1, alias__name='Serge', alias__isp=None, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile2, alias__name='Serge', alias__isp=None, ip='127.0.0.2')

    assert Alias.objects.filter(name='Serge', isp__isnull=True).count() == 2

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Serge', ip='192.168.1.10', isp=None)

    assert Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.1') == profile1
    assert Profile.objects.match_smart(name='Serge', isp=ISPFactory(), ip='127.0.0.1') == profile1
    assert Profile.objects.match_smart(name='Serge', isp=None, ip='127.0.0.2') == profile2
    assert Profile.objects.match_smart(name='Serge', isp=ISPFactory(), ip='127.0.0.2') == profile2


def test_match_smart_does_not_query_whois_if_isp_is_present(db, whois_mock):
    Profile.objects.match_smart_or_create(name='Serge', ip='1.2.3.4', isp=None)
    assert Profile.objects.get(name='Serge')
    assert not whois_mock.called


def test_match_smart_will_perform_whois_lookup_no_isp_provided(db, whois_mock):
    profile, created = Profile.objects.match_smart_or_create(name='Serge', ip='1.2.3.4')
    assert whois_mock.called
    assert created
    isp = ISP.objects.get(name='Test ISP', country='us')
    ip = IP.objects.get(isp=isp)
    assert ip.range_from == 16908288
    assert ip.range_to == 16973823


def test_match_smart_does_not_match_against_popular_names(db):
    profile = ProfileFactory()
    isp = ISPFactory()
    PlayerFactory(alias__profile=profile, alias__name='Player', alias__isp=isp, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile, alias__name='afk5min', alias__isp=isp, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile, alias__name='newname', alias__isp=isp, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile, alias__name='TODOsetname2', alias__isp=isp, ip='127.0.0.1')
    PlayerFactory(alias__profile=profile, alias__name='Serge', alias__isp=isp, ip='127.0.0.1')

    assert Profile.objects.match_smart(name='Serge', ip='127.0.0.3', isp=isp) == profile

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='Player', ip='127.0.0.3', isp=isp)
    assert Profile.objects.match_smart(name='Player', ip='127.0.0.1', isp=isp) == profile

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='TODOsetname2', ip='127.0.0.3', isp=isp)

    with pytest.raises(ObjectDoesNotExist):
        Profile.objects.match_smart(name='newname', ip='127.0.0.3', isp=isp)


def test_popular_names(db):
    popular_names = (
        'Player', 'player', 'Player2', 'player3',
        'newname', 'swat', 'lol', 'TODOsetname2231',
        'afk', 'afk5min', 'afk_dont_kick', 'killer',
        'spieler', 'gracz', 'testing', 'test', 'testing_mod',
    )
    for name in popular_names:
        assert Profile.is_name_popular(name)


class ProfileMatchTestCase(TestCase):

    def setUp(self):
        now = timezone.now()

        self.server1 = ServerFactory()
        self.server2 = ServerFactory()

        self.isp1 = ISPFactory(name='foo', country='jp')
        self.isp2 = ISPFactory(name='bar', country='uk')
        self.isp3 = ISPFactory(name='ham', country='es')

        self.profile1, self.profile2, self.profile3, self.profile4, self.profile5 = ProfileFactory.create_batch(5)

        self.alias1 = Alias.objects.create(profile=self.profile1, name='Serge', isp=self.isp1)
        self.alias2 = Alias.objects.create(profile=self.profile2, name='spam', isp=self.isp1)
        self.alias3 = Alias.objects.create(profile=self.profile3, name='django', isp=self.isp2)
        self.alias4 = Alias.objects.create(profile=self.profile4, name='python', isp=self.isp3)
        self.alias5 = Alias.objects.create(profile=self.profile5, name='bar', isp=self.isp3)

        self.game1 = GameFactory(server=self.server1, date_finished=now - timedelta(days=365))

        # game played year ago
        PlayerFactory(game=self.game1, alias=self.alias1, ip='11.11.11.11')
        PlayerFactory(game=self.game1, alias=self.alias2, ip='22.22.22.22')
        PlayerFactory(game=self.game1, alias=self.alias3, ip='44.44.44.44')
        PlayerFactory(game=self.game1, alias=self.alias4, ip='55.55.55.55')
        PlayerFactory(game=self.game1, alias=self.alias5, ip='66.66.66.77')

        # game that has just been finished
        self.game2 = GameFactory(server=self.server2, date_finished=now)

        PlayerFactory(game=self.game2,
                      alias=AliasFactory(profile=self.profile3, name='baz', isp=self.isp1),
                      ip='4.5.6.7')
        PlayerFactory(game=self.game2,
                      alias=AliasFactory(profile=self.profile3, name='bar', isp=self.isp2),
                      ip='1.2.3.4')

    def test_match_recent(self):
        obj1 = Profile.objects.match_recent(name='baz', isp=self.isp1)
        obj2 = Profile.objects.match_recent(name='bar', isp=self.isp2)
        obj3 = Profile.objects.match_recent(player__ip='1.2.3.4')
        assert obj1.pk == self.profile3.pk
        assert obj2.pk == self.profile3.pk
        assert obj3.pk == self.profile3.pk

        # old game
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_recent(player__ip='11.11.11.11')
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_recent(name='Serge', player__ip='11.11.11.11')
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_recent(name='Serge', isp=self.isp1)

        # did not participate
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_recent(name='eggs', player__ip='5.6.7.8')
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_recent(name='eggs', isp=self.isp3)

    def test_match_smart_or_create(self):
        obj, created = Profile.objects.match_smart_or_create(ip='20.20.20.20', isp=None)
        assert created

        # no args
        obj, created = Profile.objects.match_smart_or_create()
        assert created

        # different case
        obj, created = Profile.objects.match_smart_or_create(name='serge', ip='11.11.11.11', isp=None)
        assert not created

        # old game
        obj, created = Profile.objects.match_smart_or_create(ip='4.4.4.4', isp=None)
        assert created

        # different case but recently played
        obj, created = Profile.objects.match_smart_or_create(name='BAZ', ip='4.5.6.7', isp=None)
        assert not created

        # duplicate name but only the latter quilifies for recently played
        obj, created = Profile.objects.match_smart_or_create(name='BAR', ip='1.2.3.4', isp=None)
        assert not created
        obj, created = Profile.objects.match_smart_or_create(name='bar', ip='1.2.3.4', isp=None)
        assert not created

        # recent ip
        obj, created = Profile.objects.match_smart_or_create(ip='1.2.3.4', isp=None)
        assert not created

        # not recent ip
        obj, created = Profile.objects.match_smart_or_create(ip='44.44.44.44', isp=None)
        assert created

        # the ip has not been used in games
        obj, created = Profile.objects.match_smart_or_create(ip='5.6.7.8', isp=None)
        assert created

    def test_match_smart_name_country(self):
        isp1 = ISPFactory(name='spam', country='jp')
        isp2 = ISPFactory(name='eggs', country='pt')

        assert Profile.objects.match_smart(name='baz', ip='192.168.1.25', isp=isp1).pk == self.profile3.pk

        # game is recent but country doesn't match
        with pytest.raises(ObjectDoesNotExist):
            Profile.objects.match_smart(name='baz', ip='192.168.1.25', isp=isp2)


def test_player_gets_same_profile_after_name_change(db):
    isp = ISPFactory()
    profile = ProfileFactory()

    alias1 = AliasFactory(profile=profile, name='Player', isp=isp)
    PlayerFactory(alias=alias1, ip='127.0.0.1')

    alias2 = Alias.objects.match_or_create(name='Serge', ip='127.0.0.1', isp=isp)[0]
    PlayerFactory(alias=alias2, ip='127.0.0.1')

    assert alias1.pk != alias2.pk
    assert alias1.profile.pk == alias2.profile.pk


def test_player_does_not_receive_same_profile_after_long_period(db):
    isp = ISP.objects.create()
    profile = Profile.objects.create()
    now = timezone.now()

    alias1 = AliasFactory(profile=profile, name='Player', isp=isp)
    PlayerFactory(alias=alias1, ip='127.0.0.1', game__date_finished=now - timedelta(days=181))

    alias2 = Alias.objects.match_or_create(name='Serge', ip='127.0.0.1', isp=isp)[0]
    assert alias2.pk != alias1.pk
    assert alias2.profile.pk != alias1.profile.pk

    PlayerFactory(alias=alias1, ip='127.0.0.1', game__date_finished=now - timedelta(days=7))
    alias3 = Alias.objects.match_or_create(name='Another', ip='127.0.0.1', isp=isp)[0]
    assert alias3.pk != alias1.pk
    assert alias3.profile.pk == alias1.profile.pk
