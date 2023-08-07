# ruff: noqa: C408
from datetime import timedelta, datetime

import pytest
from django.utils import timezone
from pytz import UTC

from apps.geoip.factories import ISPFactory
from apps.geoip.models import ISP
from apps.tracker.exceptions import NoProfileMatchError
from apps.tracker.factories import (
    ServerFactory,
    GameFactory,
    PlayerFactory,
    ProfileFactory,
    AliasFactory,
)
from apps.tracker.managers.profile import is_name_popular
from apps.tracker.models import Profile, Alias
from apps.utils.test import freeze_timezone_now


def test_match_will_match_against_known_pair_of_name_ip(db):
    profile = ProfileFactory()
    PlayerFactory(alias__profile=profile, alias__name="Serge", alias__isp=None, ip="127.0.0.1")

    obj = Profile.objects.match(name="Serge", player__ip="127.0.0.1")
    assert obj == profile


def test_match_smart_prefers_name_ip_to_name_isp(db):
    isp1 = ISPFactory(ip="127.0.0.0/16")
    isp2 = ISPFactory(ip="192.168.0.0/16")

    profile1, profile2 = ProfileFactory.create_batch(2)
    PlayerFactory(alias__profile=profile1, alias__name="Serge", alias__isp=isp1, ip="127.0.0.1")
    PlayerFactory(alias__profile=profile2, alias__name="Serge", alias__isp=isp2, ip="192.168.1.10")

    assert (
        Profile.objects.match_smart(name="Serge", ip_address="127.0.0.1", isp=isp2).pk
        == profile1.pk
    )
    assert (
        Profile.objects.match_smart(name="Serge", ip_address="192.168.1.10", isp=isp1).pk
        == profile2.pk
    )


def test_match_smart_null_isp_does_not_match_against_existing_null_isp(db):
    profile = ProfileFactory()
    PlayerFactory(alias__profile=profile, alias__name="Serge", alias__isp=None, ip="127.0.0.1")

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="Serge", ip_address="192.168.1.10", isp=None)

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.2")

    assert Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.1") == profile


def test_match_smart_empty_isp_does_not_match_against_existing_non_null_isp(db):
    profile = ProfileFactory()
    PlayerFactory(
        alias__profile=profile, alias__name="Serge", alias__isp=ISPFactory(), ip="127.0.0.1"
    )

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.2")

    assert Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.1") == profile


def test_match_smart_will_not_match_other_profiles_with_null_isp(db):
    profile1, profile2 = ProfileFactory.create_batch(2)
    PlayerFactory(alias__profile=profile1, alias__name="Serge", alias__isp=None, ip="127.0.0.1")
    PlayerFactory(alias__profile=profile2, alias__name="Serge", alias__isp=None, ip="127.0.0.2")

    assert Alias.objects.filter(name="Serge", isp__isnull=True).count() == 2

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="Serge", ip_address="192.168.1.10", isp=None)

    assert Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.1") == profile1
    assert (
        Profile.objects.match_smart(name="Serge", isp=ISPFactory(), ip_address="127.0.0.1")
        == profile1
    )
    assert Profile.objects.match_smart(name="Serge", isp=None, ip_address="127.0.0.2") == profile2
    assert (
        Profile.objects.match_smart(name="Serge", isp=ISPFactory(), ip_address="127.0.0.2")
        == profile2
    )


def test_match_smart_does_not_query_whois_if_isp_is_present(db, whois_mock):
    Profile.objects.match_smart_or_create(name="Serge", ip_address="1.2.3.4", isp=None)
    assert Profile.objects.get(name="Serge")
    assert not whois_mock.called


def test_match_smart_will_not_perform_whois_lookup_no_isp_provided(db, whois_mock):
    profile, created = Profile.objects.match_smart_or_create(name="Serge", ip_address="1.2.3.4")

    assert not whois_mock.called
    assert created
    assert ISP.objects.count() == 0


def test_match_smart_does_not_match_against_popular_names(db):
    profile = ProfileFactory()
    isp = ISPFactory()
    PlayerFactory(alias__profile=profile, alias__name="Player", alias__isp=isp, ip="127.0.0.1")
    PlayerFactory(alias__profile=profile, alias__name="afk5min", alias__isp=isp, ip="127.0.0.1")
    PlayerFactory(alias__profile=profile, alias__name="newname", alias__isp=isp, ip="127.0.0.1")
    PlayerFactory(
        alias__profile=profile, alias__name="TODOsetname2", alias__isp=isp, ip="127.0.0.1"
    )
    PlayerFactory(alias__profile=profile, alias__name="Serge", alias__isp=isp, ip="127.0.0.1")

    assert Profile.objects.match_smart(name="Serge", ip_address="127.0.0.3", isp=isp) == profile

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="Player", ip_address="127.0.0.3", isp=isp)
    assert Profile.objects.match_smart(name="Player", ip_address="127.0.0.1", isp=isp) == profile

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="TODOsetname2", ip_address="127.0.0.3", isp=isp)

    with pytest.raises(NoProfileMatchError):
        Profile.objects.match_smart(name="newname", ip_address="127.0.0.3", isp=isp)


class TestProfileMatch:
    @pytest.fixture(autouse=True)
    def _set_up(self, db):
        now = timezone.now()

        self.server1 = ServerFactory()
        self.server2 = ServerFactory()

        self.isp1 = ISPFactory(name="foo", country="jp")
        self.isp2 = ISPFactory(name="bar", country="uk")
        self.isp3 = ISPFactory(name="ham", country="jp")
        self.isp_map = {
            "foo": self.isp1,
            "bar": self.isp2,
            "ham": self.isp3,
        }

        (
            self.profile1,
            self.profile2,
            self.profile3,
            self.profile4,
            self.profile5,
        ) = ProfileFactory.create_batch(5)

        self.alias1 = Alias.objects.create(profile=self.profile1, name="Serge", isp=self.isp1)
        self.alias2 = Alias.objects.create(profile=self.profile2, name="spam", isp=self.isp1)
        self.alias3 = Alias.objects.create(profile=self.profile3, name="django", isp=self.isp2)
        self.alias4 = Alias.objects.create(profile=self.profile4, name="python", isp=self.isp3)
        self.alias5 = Alias.objects.create(profile=self.profile5, name="bar", isp=self.isp3)

        self.game1 = GameFactory(server=self.server1, date_finished=now - timedelta(days=365))

        # game played year ago
        PlayerFactory(game=self.game1, alias=self.alias1, ip="11.11.11.11")
        PlayerFactory(game=self.game1, alias=self.alias2, ip="22.22.22.22")
        PlayerFactory(game=self.game1, alias=self.alias3, ip="44.44.44.44")
        PlayerFactory(game=self.game1, alias=self.alias4, ip="55.55.55.55")
        PlayerFactory(game=self.game1, alias=self.alias5, ip="66.66.66.77")

        # game that has just been finished
        self.game2 = GameFactory(server=self.server2, date_finished=now)

        PlayerFactory(
            game=self.game2,
            alias=AliasFactory(profile=self.profile3, name="baz", isp=self.isp1),
            ip="4.5.6.7",
        )
        PlayerFactory(
            game=self.game2,
            alias=AliasFactory(profile=self.profile3, name="bar", isp=self.isp2),
            ip="1.2.3.4",
        )

    def test_match_recent(self):
        obj1 = Profile.objects.match(recent=True, name="baz", isp=self.isp1)
        obj2 = Profile.objects.match(recent=True, name="bar", isp=self.isp2)
        obj3 = Profile.objects.match(recent=True, player__ip="1.2.3.4")
        assert obj1.pk == self.profile3.pk
        assert obj2.pk == self.profile3.pk
        assert obj3.pk == self.profile3.pk

        # old game
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match(recent=True, player__ip="11.11.11.11")
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match(recent=True, name="Serge", player__ip="11.11.11.11")
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match(recent=True, name="Serge", isp=self.isp1)

        # did not participate
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match(recent=True, name="eggs", player__ip="5.6.7.8")
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match(recent=True, name="eggs", isp=self.isp3)

    @pytest.mark.parametrize(
        "match_kwargs, is_matched",
        [
            # unknown ip
            (dict(name="Serge", ip_address="20.20.20.20", isp=None), False),
            (dict(name="serge", ip_address="20.20.20.20", isp=None), False),
            # known name+ip pair
            (dict(name="Serge", ip_address="11.11.11.11", isp=None), True),
            (dict(name="serge", ip_address="11.11.11.11", isp=None), True),
            # mismatched name+ip pair, but known name+ip pair
            (dict(name="Serge", ip_address="11.11.11.11", isp_alias="bar"), True),
            # known name+isp pair, unknown ip
            (dict(name="Serge", ip_address="5.6.7.8", isp_alias="foo"), True),
            # mismatched name+isp pair, unknown ip
            (dict(name="Serge", ip_address="5.6.7.8", isp_alias="bar"), False),
            # known name+ip pair, recently played
            (dict(name="BAZ", ip_address="4.5.6.7", isp=None), True),
            # unknown ip, known name+country pair, recently played
            (dict(name="baz", ip_address="9.9.9.9", isp_alias="ham"), True),
            (dict(name="BAZ", ip_address="9.9.9.9", isp_alias="ham"), True),
            # unknown ip, known name+country pair, but not recently played
            (dict(name="Serge", ip_address="9.9.9.9", isp_alias="ham"), False),
            # unknown name, ip matches an old game
            (dict(name="neverseen", ip_address="44.44.44.44", isp=None), False),
            # unknown name, ip matches a recent game
            (dict(name="neverseen", ip_address="1.2.3.4", isp=None), True),
            # unknown ip and name
            (dict(name="neverseen", ip_address="5.6.7.8", isp=None), False),
        ],
        ids=str,
    )
    def test_match_smart_or_create(self, match_kwargs, is_matched):
        if isp_alias := match_kwargs.pop("isp_alias", None):
            match_kwargs["isp"] = self.isp_map[isp_alias]
        obj, created = Profile.objects.match_smart_or_create(**match_kwargs)
        assert created == (not is_matched)

    def test_match_smart_name_country(self):
        isp1 = ISPFactory(name="spam", country="jp")
        isp2 = ISPFactory(name="eggs", country="pt")

        assert (
            Profile.objects.match_smart(name="baz", ip_address="192.168.1.25", isp=isp1).pk
            == self.profile3.pk
        )

        # game is recent but country doesn't match
        with pytest.raises(NoProfileMatchError):
            Profile.objects.match_smart(name="baz", ip_address="192.168.1.25", isp=isp2)


def test_player_gets_same_profile_after_name_change(db):
    ISPFactory(ip__from="127.0.0.0", ip__to="127.255.255.255")

    profile = ProfileFactory()

    alias1 = AliasFactory(profile=profile, name="Player")
    PlayerFactory(alias=alias1, ip="127.0.0.1")

    alias2 = Alias.objects.match_or_create(name="Serge", ip_address="127.0.0.1")[0]
    PlayerFactory(alias=alias2, ip="127.0.0.1")

    assert alias1.pk != alias2.pk
    assert alias1.profile.pk == alias2.profile.pk


def test_player_does_not_receive_same_profile_after_long_period(db):
    now = timezone.now()

    isp = ISPFactory(ip__from="127.0.0.0", ip__to="127.255.255.255")

    profile = ProfileFactory()

    alias1 = AliasFactory(profile=profile, name="Player", isp=isp)
    PlayerFactory(alias=alias1, ip="127.0.0.1", game__date_finished=now - timedelta(days=181))

    alias2 = Alias.objects.match_or_create(name="Serge", ip_address="127.0.0.1")[0]
    assert alias2.pk != alias1.pk
    assert alias2.profile.pk != alias1.profile.pk

    PlayerFactory(alias=alias1, ip="127.0.0.1", game__date_finished=now - timedelta(days=7))
    alias3 = Alias.objects.match_or_create(name="Another", ip_address="127.0.0.1")[0]
    assert alias3.pk != alias1.pk
    assert alias3.profile.pk == alias1.profile.pk


@pytest.mark.parametrize(
    "profile_alias_updated_at, new_alias_updated_at",
    [
        (None, datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC)),
        (
            datetime(2019, 12, 31, 11, 22, 55, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC),
        ),
        (
            datetime(2021, 2, 1, 11, 22, 55, tzinfo=timezone.utc),
            datetime(2021, 2, 1, 11, 22, 55, tzinfo=UTC),
        ),
    ],
)
@freeze_timezone_now(datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC))
def test_alias_is_created_with_existing_profile(
    now_mock, db, profile_alias_updated_at, new_alias_updated_at
):
    isp, another_isp = ISPFactory.create_batch(2)

    profile = ProfileFactory(alias_updated_at=profile_alias_updated_at)
    existing_alias = AliasFactory(profile=profile, name="Player", isp=isp)
    PlayerFactory(alias=existing_alias, ip="127.0.0.1")

    new_alias = Alias.objects.create_alias(name="Player", ip_address="127.0.0.1", isp=another_isp)
    assert new_alias.pk != existing_alias.pk

    profile.refresh_from_db()
    assert profile.alias_updated_at == new_alias_updated_at


@freeze_timezone_now(datetime(2020, 1, 1, 11, 22, 55, tzinfo=UTC))
def test_alias_is_created_with_new_profile(now_mock, db):
    isp, another_isp = ISPFactory.create_batch(2)

    profile = ProfileFactory(alias_updated_at=None)
    unaffected_alias = AliasFactory(profile=profile, name="Player", isp=isp)

    new_alias = Alias.objects.create_alias(name="Player", ip_address="127.0.0.1", isp=another_isp)
    assert new_alias.pk != unaffected_alias.pk
    assert new_alias.profile.pk != profile.pk

    profile.refresh_from_db()
    assert profile.alias_updated_at is None

    created_profile = Profile.objects.get(pk=new_alias.profile.pk)
    assert created_profile.alias_updated_at == datetime(2020, 1, 1, 11, 22, 55, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "name",
    [
        "Player",
        "player",
        "Player2",
        "player3",
        "newname",
        "swat",
        "lol",
        "TODOsetname2231",
        "afk",
        "afk5min",
        "afk_dont_kick",
        "killer",
        "spieler",
        "gracz",
        "testing",
        "test",
        "testing_mod",
    ],
)
def test_popular_names(name):
    assert is_name_popular(name)
