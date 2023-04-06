from django.core.management import call_command

from apps.tracker.factories import PlayerFactory, ProfileFactory
from apps.tracker.models import Loadout


def test_convert_loadout(db):
    empty_fields = {'primary': None, 'primary_ammo': None,
                    'secondary': None, 'secondary_ammo': None,
                    'equip_one': None, 'equip_two': None, 'equip_three': None, 'equip_four': None, 'equip_five': None,
                    'breacher': None, 'head': None, 'body': None}
    loadout1 = Loadout.objects.create(primary_legacy=10, secondary_legacy=16,
                                      equip_one_legacy=25, equip_two_legacy=25,
                                      equip_three_legacy=25, equip_four_legacy=25, equip_five_legacy=25,
                                      breacher_legacy=3, head_legacy=22, body_legacy=19,
                                      primary_ammo_legacy=16, secondary_ammo_legacy=25,
                                      **empty_fields)
    loadout2 = Loadout.objects.create(primary_legacy=10, secondary_legacy=16,
                                      equip_one_legacy=25, equip_two_legacy=25,
                                      equip_three_legacy=25, equip_four_legacy=25, equip_five_legacy=25,
                                      breacher_legacy=3, head_legacy=22, body_legacy=19,
                                      primary_ammo_legacy=16, secondary_ammo_legacy=25,
                                      **empty_fields)
    loadout3 = Loadout.objects.create(primary_legacy=10, secondary_legacy=16,
                                      equip_one_legacy=25, equip_two_legacy=25,
                                      equip_three_legacy=25, equip_four_legacy=25, equip_five_legacy=25,
                                      breacher_legacy=3, head_legacy=22, body_legacy=19,
                                      primary_ammo_legacy=16, secondary_ammo_legacy=25,
                                      **empty_fields)
    loadout4 = Loadout.objects.create(primary_legacy=10, secondary_legacy=16,
                                      equip_one_legacy=25, equip_two_legacy=25,
                                      equip_three_legacy=25, equip_four_legacy=25, equip_five_legacy=25,
                                      breacher_legacy=0, head_legacy=22, body_legacy=19,
                                      primary_ammo_legacy=16, secondary_ammo_legacy=25,
                                      **empty_fields)
    loadout5 = Loadout.objects.create(primary_legacy=10, secondary_legacy=16,
                                      equip_one_legacy=25, equip_two_legacy=25,
                                      equip_three_legacy=25, equip_four_legacy=25, equip_five_legacy=25,
                                      breacher_legacy=0, head_legacy=0, body_legacy=0,
                                      primary_ammo_legacy=0, secondary_ammo_legacy=0,
                                      **empty_fields)

    player1 = PlayerFactory(loadout=loadout2)
    player2 = PlayerFactory(loadout=loadout2)
    player3 = PlayerFactory(loadout=loadout1)
    player4 = PlayerFactory(loadout=loadout4)
    player5 = PlayerFactory(loadout=loadout5)
    player6 = PlayerFactory(loadout=loadout5)

    profile1 = ProfileFactory(loadout=loadout2)
    profile2 = ProfileFactory(loadout=loadout2)
    profile3 = ProfileFactory(loadout=loadout5)

    call_command('convert_loadout')

    player1.refresh_from_db()
    player2.refresh_from_db()
    player3.refresh_from_db()
    player4.refresh_from_db()
    player5.refresh_from_db()
    player6.refresh_from_db()

    profile1.refresh_from_db()
    profile2.refresh_from_db()
    profile3.refresh_from_db()

    assert player1.loadout_id == loadout1.pk
    assert player2.loadout_id == loadout1.pk
    assert player3.loadout_id == loadout1.pk
    assert player4.loadout_id == loadout4.pk
    assert player5.loadout_id == loadout5.pk
    assert player6.loadout_id == loadout5.pk

    assert profile1.loadout_id == loadout1.pk
    assert profile1.loadout_id == loadout1.pk
    assert profile3.loadout_id == loadout5.pk

    assert Loadout.objects.filter(pk__in=[loadout2.pk, loadout3.pk]).count() == 0
