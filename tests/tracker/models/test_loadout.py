import pytest
from django.db import DataError, IntegrityError

from apps.tracker.models import Loadout
from tests.factories.loadout import LoadoutFactory

fields = [
    "primary",
    "primary_ammo",
    "secondary",
    "secondary_ammo",
    "equip_one",
    "equip_two",
    "equip_three",
    "equip_four",
    "equip_five",
    "breacher",
    "head",
    "body",
]


@pytest.mark.django_db
def test_obtain_loadout():
    empty_loadout = Loadout.objects.obtain()
    for slot in fields:
        assert getattr(empty_loadout, slot) == "None"

    semi_full_loadout = LoadoutFactory(
        primary="9mm SMG", secondary="Taser Stun Gun", breacher="Shotgun"
    )
    full_loadout = LoadoutFactory(
        primary="9mm SMG",
        secondary="Taser Stun Gun",
        breacher="Shotgun",
        head="Gas Mask",
        body="Light Armor",
    )

    assert (
        Loadout.objects.obtain(
            primary="9mm SMG",
            secondary="Taser Stun Gun",
            breacher="Shotgun",
            head="None",
            body=None,
        )
        == semi_full_loadout
    )

    assert (
        Loadout.objects.obtain(
            primary="9mm SMG",
            secondary="Taser Stun Gun",
            breacher="Shotgun",
            head="Gas Mask",
            body="Light Armor",
        )
        == full_loadout
    )

    # invalid equipment name
    with pytest.raises(DataError):
        LoadoutFactory(primary="m4")


@pytest.mark.django_db
def test_duplicate_loadout():
    loadout_kwargs = dict.fromkeys(fields, "None")
    loadout_kwargs["primary"] = "9mm SMG"
    assert Loadout.objects.create(**loadout_kwargs)

    with pytest.raises(IntegrityError):
        Loadout.objects.create(**loadout_kwargs)
