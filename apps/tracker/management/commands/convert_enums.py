import logging

from django.core.management.base import BaseCommand
from django.db import connection


logger = logging.getLogger(__name__)


gametype_mapping = {
    0: 'Barricaded Suspects',
    1: 'VIP Escort',
    2: 'Rapid Deployment',
    3: 'CO-OP',
    4: 'Smash And Grab',
    5: 'CO-OP QMM',
}

outcome_mapping = {
    1: 'swat_bs',
    2: 'sus_bs',
    3: 'swat_rd',
    4: 'sus_rd',
    5: 'tie',
    6: 'swat_vip_escape',
    7: 'sus_vip_good_kill',
    8: 'swat_vip_bad_kill',
    9: 'sus_vip_bad_kill',
    10: 'coop_completed',
    11: 'coop_failed',
    12: 'swat_sg',
    13: 'sus_sg',
}

team_mapping = {
    0: 'swat',
    1: 'suspects',
}

coop_status_mapping = {
    1: 'Ready',
    2: 'Healthy',
    3: 'Injured',
    4: 'Incapacitated'
}

equipment_mapping = {
    0: 'None',
    1: 'M4 Super90',
    2: 'Nova Pump',
    3: 'Shotgun',
    4: 'Less Lethal Shotgun',
    5: 'Pepper-ball',
    6: 'Colt M4A1 Carbine',
    7: 'AK-47 Machinegun',
    8: 'GB36s Assault Rifle',
    9: 'Gal Sub-machinegun',
    10: '9mm SMG',
    11: 'Suppressed 9mm SMG',
    12: '.45 SMG',
    13: 'M1911 Handgun',
    14: '9mm Handgun',
    15: 'Colt Python',
    16: 'Taser Stun Gun',
    17: 'VIP Colt M1911 Handgun',
    18: 'CS Gas VIP',
    19: 'Light Armor',
    20: 'Heavy Armor',
    21: 'Gas Mask',
    22: 'Helmet',
    23: 'Flashbang',
    24: 'CS Gas',
    25: 'Stinger',
    26: 'Pepper Spray',
    27: 'Optiwand',
    28: 'Toolkit',
    29: 'Door Wedge',
    30: 'C2 (x3)',
    31: 'The Detonator',
    32: 'Zip-cuffs',
    33: 'IAmCuffed',
    34: 'Colt Accurized Rifle',
    35: '40mm Grenade Launcher',
    36: '5.56mm Light Machine Gun',
    37: '5.7x28mm Submachine Gun',
    38: 'Mark 19 Semi-Automatic Pistol',
    39: '9mm Machine Pistol',
    40: 'Cobra Stun Gun',
    41: 'Ammo Pouch',
    42: 'No Armor',
    43: 'Night Vision Goggles',
    44: 'Stinger Grenade',
    45: 'CS Gas Grenade',
    46: 'Flashbang Grenade',
    47: 'Baton Grenade',
}

objective_mapping = {
    0: 'Rendezvous with Jennings',
    1: 'Avoid civilian injuries',
    2: 'Avoid officer injuries',
    3: 'Avoid officer casualties',
    4: 'Avoid suspect casualties',
    5: 'Avoid injuries to yourself',
    6: 'Debrief before the timer expires',
    7: 'Find and deactivate the bombs',
    8: 'Find and disarm the bombs!',
    9: 'Investigate the laundromat',
    10: 'Neutralize Alice Jenkins',
    11: 'Bring order to chaos',
    12: 'Neutralize Javier Arias',
    13: 'Neutralize Andrew Taronne',
    14: 'Neutralize Anton Georgiev',
    15: 'Neutralize Simon Gowan',
    16: 'Neutralize Lian Niu',
    17: 'Neutralize Alex Jimenez',
    18: 'Neutralize Lawrence Fairfax',
    19: 'Neutralize Kiril Stetchkov',
    20: 'Neutralize Hadeon Koshka',
    21: 'Neutralize Allen Kruse',
    22: 'Neutralize Andrew Norman',
    23: 'Neutralize Jean Trouffant',
    24: 'Neutralize Todor Stetchkov',
    25: 'Rescue Lawrence Adams',
    26: 'Rescue all of the civilians',
    27: 'Rescue Gary Altman',
    28: 'Arrest Louie Baccus',
    29: 'Rescue James Betincourt',
    30: 'Rescue Oscar Bogard',
    31: 'Rescue Warren Rooney',
    32: 'Rescue Hyun-Jun Park',
    33: 'Rescue Willis Fischer',
    34: 'Rescue Melinda Kline',
    35: 'Rescue Lionel Macarthur',
    36: 'Rescue Heidi Rosenstein',
    37: 'Rescue Dr. Theodore Sturgeon',
    38: 'Rescue Kim Dong Yin',
    39: 'Rescue Detective Walsh',
    40: 'Locate Officer Wilkins',
    41: 'Rescue Rita Winston',
    42: 'Secure the briefcase',
    43: 'Secure the MAC-10',
}

objective_status_mapping = {
    0: 'In Progress',
    1: 'Completed',
    2: 'Failed',
}

procedure_mapping = {
    0: 'Suspects incapacitated',
    1: 'Suspects arrested',
    2: 'Mission completed',
    3: 'Failed to report a downed officer',
    4: 'Suspects neutralized',
    5: 'No civilians injured',
    6: 'Incapacitated a hostage',
    7: 'Killed a hostage',
    8: 'Incapacitated a fellow officer',
    9: 'Injured a fellow officer',
    10: 'No officers down',
    11: 'No suspects neutralized',
    12: 'Unauthorized use of deadly force',
    13: 'Unauthorized use of force',
    14: 'Player uninjured',
    15: 'Failed to prevent destruction of evidence.',
    16: 'Failed to apprehend fleeing suspect.',
    17: 'Report status to TOC',
    18: 'All evidence secured',
}


def convert_column(table_name, column_name, enum_name, value_mapping):
    with connection.cursor() as cursor:
        for value_id, value_enum in value_mapping.items():
            logger.info('converting %s.%s->%s %s->%s', table_name, column_name, enum_name, value_id, value_enum)
            cursor.execute(f"""UPDATE "{table_name}" SET "{enum_name}" = %s
                               WHERE "{enum_name}" IS NULL AND "{column_name}" = %s""",
                           [value_enum, str(value_id)])


class Command(BaseCommand):

    def handle(self, *args, **options):
        convert_column('tracker_game', 'gametype', 'gametype_enum', gametype_mapping)
        convert_column('tracker_game', 'outcome', 'outcome_enum', outcome_mapping)

        with connection.cursor() as cursor:
            for gametype in ['Barricaded Suspects', 'VIP Escort', 'Rapid Deployment', 'Smash And Grab']:
                cursor.execute("""UPDATE tracker_player SET coop_status_enum = NULL
                                  WHERE coop_status_enum IS NOT NULL AND
                                  game_id IN (SELECT id FROM tracker_game WHERE gametype_enum = %s)""",
                               [gametype])
        convert_column('tracker_player', 'coop_status', 'coop_status_enum', coop_status_mapping)

        convert_column('tracker_profile', 'team', 'team_enum', team_mapping)
        convert_column('tracker_player', 'team', 'team_enum', team_mapping)

        convert_column('tracker_weapon', 'name', 'name_enum', equipment_mapping)

        convert_column('tracker_objective', 'name', 'name_enum', objective_mapping)
        convert_column('tracker_objective', 'status', 'status_enum', objective_status_mapping)
        convert_column('tracker_procedure', 'name', 'name_enum', procedure_mapping)
