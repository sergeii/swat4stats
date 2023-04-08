import pytest
from django.core.management import call_command

from apps.tracker.factories import LoadoutFactory, PlayerFactory
from apps.tracker.models import Loadout


@pytest.mark.parametrize('empty_loadout_exists', [True, False])
def test_fill_empty_loadout(db, empty_loadout_exists):
    if empty_loadout_exists:
        LoadoutFactory()

    loadout = Loadout.objects.create(
        primary='9mm SMG',
        primary_legacy=10,
        secondary='Taser Stun Gun',
        secondary_legacy=16,
        equip_one='Stinger',
        equip_one_legacy=25,
        equip_two='Stinger',
        equip_two_legacy=25,
        equip_three='Stinger',
        equip_three_legacy=25,
        equip_four='Stinger',
        equip_four_legacy=25,
        equip_five='Stinger',
        equip_five_legacy=25,
        breacher='Shotgun',
        breacher_legacy=3,
        head='Helmet',
        head_legacy=22,
        body='Light Armor',
        body_legacy=19,
        primary_ammo='MP5SMG_FMJ',
        primary_ammo_legacy=16,
        secondary_ammo='TaserAmmo',
        secondary_ammo_legacy=25
    )

    player1 = PlayerFactory(loadout=None)
    player2 = PlayerFactory(loadout=loadout)
    player3 = PlayerFactory(loadout=None)

    call_command('fill_empty_loadout')

    empty_loadout = Loadout.objects.get(
        primary='None',
        primary_ammo='None',
        secondary='None',
        secondary_ammo='None',
        equip_one='None',
        equip_two='None',
        equip_three='None',
        equip_four='None',
        equip_five='None',
        breacher='None',
        head='None',
        body='None',
    )
    for field in [
        'primary_legacy',
        'primary_ammo_legacy',
        'secondary_legacy',
        'secondary_ammo_legacy',
        'equip_one_legacy',
        'equip_two_legacy',
        'equip_three_legacy',
        'equip_four_legacy',
        'equip_five_legacy',
        'breacher_legacy',
        'head_legacy',
        'body_legacy',
    ]:
        assert getattr(empty_loadout, field) == 0

    for p in [player1, player2, player3]:
        p.refresh_from_db()

    assert player1.loadout_id == empty_loadout.pk
    assert player2.loadout_id == loadout.pk
    assert player3.loadout_id == empty_loadout.pk
