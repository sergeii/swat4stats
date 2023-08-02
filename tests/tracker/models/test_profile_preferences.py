from datetime import timedelta

import pytest
from django.utils import timezone

from apps.geoip.factories import ISPFactory
from apps.tracker.factories import (
    LoadoutFactory,
    PlayerFactory,
    ProfileFactory,
    RandomLoadoutFactory,
)
from apps.utils.test import freeze_timezone_now


@pytest.fixture(autouse=True)
def _min_preferred_games(settings):
    settings.TRACKER_PREFERRED_GAMES = 5


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_name_over_recent_games(db):
    profile = ProfileFactory()

    assert profile.fetch_preferred_name() is None

    PlayerFactory(alias__profile=profile, alias__name="Serge")
    assert profile.fetch_preferred_name() == "Serge"

    PlayerFactory.create_batch(4, alias__profile=profile, alias__name="|MYT|Serge")
    assert profile.fetch_preferred_name() == "|MYT|Serge"

    PlayerFactory.create_batch(3, alias__profile=profile, alias__name="AFK")
    assert profile.fetch_preferred_name() == "AFK"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_country(db):
    profile = ProfileFactory()
    isp1 = ISPFactory(country="un")
    isp2 = ISPFactory(country="eu")
    isp3 = ISPFactory(country="uk")

    assert profile.fetch_preferred_country() is None

    PlayerFactory(alias__profile=profile, alias__isp=isp1)
    assert profile.fetch_preferred_country() == "un"

    PlayerFactory.create_batch(4, alias__profile=profile, alias__isp=isp2)
    assert profile.fetch_preferred_country() == "eu"

    PlayerFactory.create_batch(3, alias__profile=profile, alias__isp=isp3)
    assert profile.fetch_preferred_country() == "uk"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_team(db):
    profile = ProfileFactory()

    assert profile.fetch_preferred_team() is None

    PlayerFactory(alias__profile=profile, team="swat")
    assert profile.fetch_preferred_team() == "swat"

    PlayerFactory.create_batch(2, alias__profile=profile, team="swat")
    assert profile.fetch_preferred_team() == "swat"

    PlayerFactory.create_batch(3, alias__profile=profile, team="suspects")
    assert profile.fetch_preferred_team() == "suspects"


@pytest.mark.django_db(databases=["default", "replica"])
def test_preferred_loadout(db):
    profile = ProfileFactory()
    empty_loadout = LoadoutFactory()
    another_loadout = LoadoutFactory(primary="9mm SMG", secondary="Taser Stun Gun")

    assert profile.fetch_preferred_loadout() is None

    PlayerFactory(alias__profile=profile, loadout=empty_loadout)
    assert profile.fetch_preferred_loadout() == empty_loadout.pk

    PlayerFactory.create_batch(4, alias__profile=profile, loadout=empty_loadout)
    assert profile.fetch_preferred_loadout() == empty_loadout.pk

    PlayerFactory.create_batch(3, alias__profile=profile, loadout=another_loadout)
    assert profile.fetch_preferred_loadout() == another_loadout.pk


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_preferences(db):
    now = timezone.now()
    initial_loadout = RandomLoadoutFactory()
    another_loadout = RandomLoadoutFactory()
    profile = ProfileFactory(name="Player", team="swat", country="eu", loadout=initial_loadout)

    with freeze_timezone_now(now):
        profile.update_preferences()

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
        profile.update_preferences()

    profile.refresh_from_db()
    assert profile.name == "Serge"
    assert profile.country == "un"
    assert profile.team == "suspects"
    assert profile.team_legacy == 1
    assert profile.loadout == another_loadout
    assert profile.preferences_updated_at == now + timedelta(hours=1)
