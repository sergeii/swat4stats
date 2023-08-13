from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tracker.models import Profile
from apps.utils.test import freeze_timezone_now
from tests.factories.geoip import ISPFactory
from tests.factories.tracker import PlayerFactory, ProfileFactory
from tests.factories.loadout import LoadoutFactory, RandomLoadoutFactory


@pytest.fixture(autouse=True)
def _min_preferred_games(settings):
    settings.TRACKER_PREFERRED_GAMES = 5


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_name_over_recent_games():
    profile = ProfileFactory()

    assert Profile.objects.fetch_preferred_name_for_profile(profile) is None

    PlayerFactory(alias__profile=profile, alias__name="Serge")
    assert Profile.objects.fetch_preferred_name_for_profile(profile) == "Serge"

    PlayerFactory.create_batch(4, alias__profile=profile, alias__name="|MYT|Serge")
    assert Profile.objects.fetch_preferred_name_for_profile(profile) == "|MYT|Serge"

    PlayerFactory.create_batch(3, alias__profile=profile, alias__name="AFK")
    assert Profile.objects.fetch_preferred_name_for_profile(profile) == "AFK"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_country():
    profile = ProfileFactory()
    isp1 = ISPFactory(country="un")
    isp2 = ISPFactory(country="eu")
    isp3 = ISPFactory(country="uk")

    assert Profile.objects.fetch_preferred_country_for_profile(profile) is None

    PlayerFactory(alias__profile=profile, alias__isp=isp1)
    assert Profile.objects.fetch_preferred_country_for_profile(profile) == "un"

    PlayerFactory.create_batch(4, alias__profile=profile, alias__isp=isp2)
    assert Profile.objects.fetch_preferred_country_for_profile(profile) == "eu"

    PlayerFactory.create_batch(3, alias__profile=profile, alias__isp=isp3)
    assert Profile.objects.fetch_preferred_country_for_profile(profile) == "uk"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_team():
    profile = ProfileFactory()

    assert Profile.objects.fetch_preferred_team_for_profile(profile) is None

    PlayerFactory(alias__profile=profile, team="swat")
    assert Profile.objects.fetch_preferred_team_for_profile(profile) == "swat"

    PlayerFactory.create_batch(2, alias__profile=profile, team="swat")
    assert Profile.objects.fetch_preferred_team_for_profile(profile) == "swat"

    PlayerFactory.create_batch(3, alias__profile=profile, team="suspects")
    assert Profile.objects.fetch_preferred_team_for_profile(profile) == "suspects"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_loadout():
    profile = ProfileFactory()
    empty_loadout = LoadoutFactory()
    another_loadout = LoadoutFactory(primary="9mm SMG", secondary="Taser Stun Gun")

    assert Profile.objects.fetch_preferred_loadout_for_profile(profile) is None

    PlayerFactory(alias__profile=profile, loadout=empty_loadout)
    assert Profile.objects.fetch_preferred_loadout_for_profile(profile) == empty_loadout.pk

    PlayerFactory.create_batch(4, alias__profile=profile, loadout=empty_loadout)
    assert Profile.objects.fetch_preferred_loadout_for_profile(profile) == empty_loadout.pk

    PlayerFactory.create_batch(3, alias__profile=profile, loadout=another_loadout)
    assert Profile.objects.fetch_preferred_loadout_for_profile(profile) == another_loadout.pk


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_preferences():
    now = timezone.now()
    initial_loadout = RandomLoadoutFactory()
    another_loadout = RandomLoadoutFactory()
    profile = ProfileFactory(name="Player", team="swat", country="eu", loadout=initial_loadout)

    with freeze_timezone_now(now):
        Profile.objects.update_preferences_for_profile(profile)

    profile.refresh_from_db()
    assert profile.name == "Player"
    assert profile.country == "eu"
    assert profile.team == "swat"
    assert profile.loadout == initial_loadout
    assert profile.preferences_updated_at is None

    PlayerFactory.create_batch(
        2,
        alias__name="Serge",
        alias__profile=profile,
        alias__isp__country="un",
        team="suspects",
        loadout=another_loadout,
    )
    with freeze_timezone_now(now + timedelta(hours=1)):
        Profile.objects.update_preferences_for_profile(profile)

    profile.refresh_from_db()
    assert profile.name == "Serge"
    assert profile.country == "un"
    assert profile.team == "suspects"
    assert profile.team_legacy == 1
    assert profile.loadout == another_loadout
    assert profile.preferences_updated_at == now + timedelta(hours=1)
