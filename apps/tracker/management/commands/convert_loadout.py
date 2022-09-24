import logging

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.tracker.management.commands.convert_enums import convert_column, equipment_mapping
from apps.tracker.models import Loadout, Player, Profile

logger = logging.getLogger(__name__)


ammo_mapping = {
    0: 'None',
    1: 'M4Super90SGAmmo',
    2: 'M4Super90SGSabotAmmo',
    3: 'NovaPumpSGAmmo',
    4: 'NovaPumpSGSabotAmmo',
    5: 'LessLethalAmmo',
    6: 'CSBallLauncherAmmo',
    7: 'M4A1MG_JHP',
    8: 'M4A1MG_FMJ',
    9: 'AK47MG_FMJ',
    10: 'AK47MG_JHP',
    11: 'G36kMG_FMJ',
    12: 'G36kMG_JHP',
    13: 'UZISMG_FMJ',
    14: 'UZISMG_JHP',
    15: 'MP5SMG_JHP',
    16: 'MP5SMG_FMJ',
    17: 'UMP45SMG_FMJ',
    18: 'UMP45SMG_JHP',
    19: 'ColtM1911HG_JHP',
    20: 'ColtM1911HG_FMJ',
    21: 'Glock9mmHG_JHP',
    22: 'Glock9mmHG_FMJ',
    23: 'PythonRevolverHG_FMJ',
    24: 'PythonRevolverHG_JHP',
    25: 'TaserAmmo',
    26: 'VIPPistolAmmo_FMJ',
    27: 'ColtAR_FMJ',
    28: 'HK69GL_StingerGrenadeAmmo',
    29: 'HK69GL_FlashbangGrenadeAmmo',
    30: 'HK69GL_CSGasGrenadeAmmo',
    31: 'HK69GL_TripleBatonAmmo',
    32: 'SAWMG_JHP',
    33: 'SAWMG_FMJ',
    34: 'FNP90SMG_FMJ',
    35: 'FNP90SMG_JHP',
    36: 'DEHG_FMJ',
    37: 'DEHG_JHP',
    38: 'TEC9SMG_FMJ',
}


class Command(BaseCommand):

    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)

        equip_slots = ['primary', 'secondary',
                       'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five',
                       'breacher', 'head', 'body']
        ammo_slots = ['primary_ammo', 'secondary_ammo']
        loadout_slots = equip_slots + ammo_slots
        loadout_slots_legacy = [f'{field}_legacy' for field in loadout_slots]

        duplicate_loadout = (Loadout.objects
                             .order_by()
                             .values(*loadout_slots_legacy)
                             .annotate(cnt=Count('pk'))
                             .filter(cnt__gt=1)
                             .values(*loadout_slots_legacy))

        for loadout_items in duplicate_loadout:
            dup_loadout_qs = Loadout.objects.filter(**loadout_items).order_by('pk')
            main_loadout_id = list(dup_loadout_qs.values_list('pk', flat=True))[0]
            loadout_items_to_merge = list(dup_loadout_qs.exclude(pk=main_loadout_id).values_list('pk', flat=True))
            logger.info('merging loadout ids %s to %s', loadout_items_to_merge, main_loadout_id)
            Player.objects.filter(loadout_id__in=loadout_items_to_merge).update(loadout_id=main_loadout_id)
            Profile.objects.filter(loadout_id__in=loadout_items_to_merge).update(loadout_id=main_loadout_id)
            logger.info('deleting loadout ids %s', loadout_items_to_merge)
            Loadout.objects.filter(pk__in=loadout_items_to_merge).delete()

        for slot in equip_slots:
            convert_column('tracker_loadout', slot, f'{slot}_enum', equipment_mapping)

        for slot in ammo_slots:
            convert_column('tracker_loadout', slot, f'{slot}_enum', ammo_mapping)
