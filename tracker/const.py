# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from julia import node


EQUIPMENT = {
    '0': 'None',
    '1': 'M4 Super90',
    '2': 'Nova Pump',
    '3': 'Shotgun',
    '4': 'Less Lethal Shotgun',
    '5': 'Pepper-ball',
    '6': 'Colt M4A1 Carbine',
    '7': 'AK-47 Machinegun',
    '8': 'GB36s Assault Rifle',
    '9': 'Gal Sub-machinegun',
    '10': '9mm SMG',
    '11': 'Suppressed 9mm SMG',
    '12': '.45 SMG',
    '13': 'M1911 Handgun',
    '14': '9mm Handgun',
    '15': 'Colt Python',
    '16': 'Taser Stun Gun',
    '17': 'VIP Colt M1911 Handgun',
    '18': 'CS Gas',
    '19': 'Light Armor',
    '20': 'Heavy Armor',
    '21': 'Gas Mask',
    '22': 'Helmet',
    '23': 'Flashbang',
    '24': 'CS Gas',
    '25': 'Stinger',
    '26': 'Pepper Spray',
    '27': 'Optiwand',
    '28': 'Toolkit',
    '29': 'Door Wedge',
    '30': 'C2 (x3)',
    '31': 'The Detonator',
    '32': 'Zip-cuffs',
    '33': 'IAmCuffed',
    '34': 'Colt Accurized Rifle',
    '35': '40mm Grenade Launcher',
    '36': '5.56mm Light Machine Gun',
    '37': '5.7x28mm Submachine Gun',
    '38': 'Mark 19 Semi-Automatic Pistol',
    '39': '9mm Machine Pistol',
    '40': 'Cobra Stun Gun',
    '41': 'Ammo Pouch',
    '42': 'No Armor',
    '43': 'Night Vision Goggles',
    '44': 'Stinger',
    '45': 'CS Gas',
    '46': 'Flashbang',
    '47': 'Baton',
}

AMMO = {
    '0': 'None',
    '1': 'M4Super90SGAmmo',
    '2': 'M4Super90SGSabotAmmo',
    '3': 'NovaPumpSGAmmo',
    '4': 'NovaPumpSGSabotAmmo',
    '5': 'LessLethalAmmo',
    '6': 'CSBallLauncherAmmo',
    '7': 'M4A1MG_JHP',
    '8': 'M4A1MG_FMJ',
    '9': 'AK47MG_FMJ',
    '10': 'AK47MG_JHP',
    '11': 'G36kMG_FMJ',
    '12': 'G36kMG_JHP',
    '13': 'UZISMG_FMJ',
    '14': 'UZISMG_JHP',
    '15': 'MP5SMG_JHP',
    '16': 'MP5SMG_FMJ',
    '17': 'UMP45SMG_FMJ',
    '18': 'UMP45SMG_JHP',
    '19': 'ColtM1911HG_JHP',
    '20': 'ColtM1911HG_FMJ',
    '21': 'Glock9mmHG_JHP',
    '22': 'Glock9mmHG_FMJ',
    '23': 'PythonRevolverHG_FMJ',
    '24': 'PythonRevolverHG_JHP',
    '25': 'TaserAmmo',
    '26': 'VIPPistolAmmo_FMJ',
    '27': 'ColtAR_FMJ',
    '28': 'HK69GL_StingerGrenadeAmmo',
    '29': 'HK69GL_FlashbangGrenadeAmmo',
    '30': 'HK69GL_CSGasGrenadeAmmo',
    '31': 'HK69GL_TripleBatonAmmo',
    '32': 'SAWMG_JHP',
    '33': 'SAWMG_FMJ',
    '34': 'FNP90SMG_FMJ',
    '35': 'FNP90SMG_JHP',
    '36': 'DEHG_FMJ',
    '37': 'DEHG_JHP',
    '38': 'TEC9SMG_FMJ',
}

STREAM_PATTERN = {
    # Unique identifier for this particular data set
    '0': {
        'type': node.StringPatternNode,
        'name': 'tag',
        'required': True,
    },
    # Mod version
    '1': {
        'type': node.StringPatternNode,
        'name': 'version',
        'required': True,
    },
    # Join port number
    '2': {
        'type': node.NumericPatternNode,
        'name': 'port',
        'required': True,
    },
    # Server time in the format of Unix Timestamp
    # The server declares itself to be in UTC timezone, which makes this value untrustworthy
    # On the other hand this is an excellent argument value for hashing
    '3': {
        'type': node.NumericPatternNode,
        'name': 'timestamp',
        'required': True,
    },
    # Last 32 bits of an md5 encoded request signature hash
    # The original hash is a product of the following parameters:
    # `server key` + `join port` + `timestamp`
    '4': {
        'type': node.StringPatternNode,
        'name': 'hash',
        'required': True,
    },
    # Game title
    '5': {
        'type': node.MappingPatternNode,
        'name': 'gamename',
        'required': False,
        'default': '0',
        'table': {
            '0': 'SWAT 4',
            '1': 'SWAT 4X',
        }
    },
    # Game version
    '6': {
        'type': node.StringPatternNode,
        'name': 'gamever',
        'required': True,
    },
    # Hostname
    '7': {
        'type': node.StringPatternNode,
        'name': 'hostname',
        'required': True,
    },
    # Gametype
    '8': {
        'type': node.MappingPatternNode,
        'name': 'gametype',
        'required': False,
        'default': '0',
        'table': {
            '0': 'Barricaded Suspects',
            '1': 'VIP Escort',
            '2': 'Rapid Deployment',
            '3': 'CO-OP',
            '4': 'Smash And Grab',
            #'5': 'CO-OP QMM',
        }
    },
    # Map
    '9': {
        'type': node.MappingPatternNode,
        'name': 'mapname',
        'required': False,
        'default': '0',
        'table': {
            '0': 'A-Bomb Nightclub',
            '1': 'Brewer County Courthouse',
            '2': 'Children of Taronne Tenement',
            '3': 'DuPlessis Diamond Center',
            '4': 'Enverstar Power Plant',
            '5': 'Fairfax Residence',
            '6': 'Food Wall Restaurant',
            '7': 'Meat Barn Restaurant',
            '8': 'Mt. Threshold Research Center',
            '9': 'Northside Vending',
            '10': 'Old Granite Hotel',
            '11': 'Qwik Fuel Convenience Store',
            '12': 'Red Library Offices',
            '13': 'Riverside Training Facility',
            '14': 'St. Michael\'s Medical Center',
            '15': 'The Wolcott Projects',
            '16': 'Victory Imports Auto Center',
            '17': '-EXP- Department of Agriculture',
            '18': '-EXP- Drug Lab',
            '19': '-EXP- Fresnal St. Station',
            '20': '-EXP- FunTime Amusements',
            '21': '-EXP- Sellers Street Auditorium',
            '22': '-EXP- Sisters of Mercy Hostel',
            '23': '-EXP- Stetchkov Warehouse',
        },
    },
    # Indicate whether the server is password protected
    '10': {
        'type': node.BooleanPatternNode,
        'name': 'passworded',
        'required': False,
        'default': '0',
    },
    # Player count
    '11': {
        'type': node.NumericPatternNode,
        'name': 'player_num',
        'required': True,
    },
    # Player limit
    '12': {
        'type': node.NumericPatternNode,
        'name': 'player_max',
        'required': True,
    },
    # Round index
    '13': {
        'type': node.NumericPatternNode,
        'name': 'round_num',
        'required': False,
        'default': '0',
    },
    # Rounds per map
    '14': {
        'type': node.NumericPatternNode,
        'name': 'round_max',
        'required': True,
    },
    # Time elapsed since the round start
    '15': {
        'type': node.NumericPatternNode,
        'name': 'time_absolute',
        'required': True,
    },
    # Time the game has actually span
    '16': {
        'type': node.NumericPatternNode,
        'name': 'time',
        'required': True,
    },
    # Round time limit
    '17': {
        'type': node.NumericPatternNode,
        'name': 'time_limit',
        'required': True,
    },
    # Number of SWAT victories
    '18': {
        'type': node.NumericPatternNode,
        'name': 'vict_swat',
        'required': False,
        'default': '0',
    },
    # Number of Suspects victories
    '19': {
        'type': node.NumericPatternNode,
        'name': 'vict_sus',
        'required': False,
        'default': '0',
    },
    # SWAT score
    '20': {
        'type': node.NumericPatternNode,
        'name': 'score_swat',
        'required': False,
        'default': '0',
    },
    # Suspects score
    '21': {
        'type': node.NumericPatternNode,
        'name': 'score_sus',
        'required': False,
        'default': '0',
    },
    # Round outcome
    '22': {
        'type': node.MappingPatternNode,
        'name': 'outcome',
        'required': True,
        'table': {
            '0' : 'none',
            '1' : 'swat_bs',            # SWAT victory in Barricaded Suspects
            '2' : 'sus_bs',             # Suspects victory in Barricaded Suspects
            '3' : 'swat_rd',            # SWAT victory in Rapid Deployment (all bombs have been exploded)
            '4' : 'sus_rd',             # Suspects victory in Rapid Deployment (all bombs have been deactivated)
            '5' : 'tie',                # A tie
            '6' : 'swat_vip_escape',    # SWAT victory in VIP Escort - The VIP has escaped
            '7' : 'sus_vip_good_kill',  # Suspects victory in VIP Escort - Suspects have executed the VIP
            '8' : 'swat_vip_bad_kill',  # SWAT victory in VIP Escort - Suspects have killed the VIP
            '9' : 'sus_vip_bad_kill',   # Suspects victory in VIP Escort - SWAT have killed the VIP
            '10': 'coop_completed',     # COOP objectives have been completed
            '11': 'coop_failed',        # COOP objectives have been failed
            '12': 'swat_sg',            # SWAT victory in Smash and Grab
            '13': 'sus_sg',             # Suspects victory in Smash and Grab
        },
    },
    # Number of bombs defused
    '23': {
        'type': node.NumericPatternNode,
        'name': 'bombs_defused',
        'required': False,
        'default': '0',
    },
    # Total number of points
    '24': {
        'type': node.NumericPatternNode,
        'name': 'bombs_total',
        'required': False,
        'default': '0',
    },
    # List of COOP objectives
    '25': {
        'type': node.ListPatternNode,
        'name': 'coop_objectives',
        'required': False,
        'item': {
            'type': node.DictPatternNode,
            'items': {
                '0': {
                    'type': node.MappingPatternNode,
                    'name': 'name',
                    'required': True,
                    'table': {
                        '0' : 'Arrest_Jennings',
                        '1' : 'Custom_NoCiviliansInjured',
                        '2' : 'Custom_NoOfficersInjured',
                        '3' : 'Custom_NoOfficersKilled',
                        '4' : 'Custom_NoSuspectsKilled',
                        '5' : 'Custom_PlayerUninjured',
                        '6' : 'Custom_Timed',
                        '7' : 'Disable_Bombs',
                        '8' : 'Disable_Office_Bombs',
                        '9' : 'Investigate_Laundromat',
                        '10': 'Neutralize_Alice',
                        '11': 'Neutralize_All_Enemies',
                        '12': 'Neutralize_Arias',
                        '13': 'Neutralize_CultLeader',
                        '14': 'Neutralize_Georgiev',
                        '15': 'Neutralize_Grover',
                        '16': 'Neutralize_GunBroker',
                        '17': 'Neutralize_Jimenez',
                        '18': 'Neutralize_Killer',
                        '19': 'Neutralize_Kiril',
                        '20': 'Neutralize_Koshka',
                        '21': 'Neutralize_Kruse',
                        '22': 'Neutralize_Norman',
                        '23': 'Neutralize_TerrorLeader',
                        '24': 'Neutralize_Todor',
                        '25': 'Rescue_Adams',
                        '26': 'Rescue_All_Hostages',
                        '27': 'Rescue_Altman',
                        '28': 'Rescue_Baccus',
                        '29': 'Rescue_Bettencourt',
                        '30': 'Rescue_Bogard',
                        '31': 'Rescue_CEO',
                        '32': 'Rescue_Diplomat',
                        '33': 'Rescue_Fillinger',
                        '34': 'Rescue_Kline',
                        '35': 'Rescue_Macarthur',
                        '36': 'Rescue_Rosenstein',
                        '37': 'Rescue_Sterling',
                        '38': 'Rescue_Victims',
                        '39': 'Rescue_Walsh',
                        '40': 'Rescue_Wilkins',
                        '41': 'Rescue_Winston',
                        '42': 'Secure_Briefcase',
                        '43': 'Secure_Weapon',
                    },
                },
                '1': {
                    'type': node.MappingPatternNode,
                    'name': 'status',
                    'required': False,
                    'default': '1',
                    'table': {
                        '0': 'progress',
                        '1': 'completed',
                        '2': 'failed',
                    },
                },
            },
        },
    },
    # List of COOP procedures
    '26': {
        'type': node.ListPatternNode,
        'name': 'coop_procedures',
        'required': False,
        'item': {
            'type': node.DictPatternNode,
            'items': {
                '0': {
                    'type': node.MappingPatternNode,
                    'name': 'name',
                    'required': True,
                    'table': {
                        '0' : 'bonus_suspect_incapped',
                        '1' : 'bonus_suspect_arrested',
                        '2' : 'bonus_mission_completed',
                        '3' : 'penalty_officer_unevacuated',
                        '4' : 'bonus_suspect_killed',
                        '5' : 'bonus_all_hostages_uninjured',
                        '6' : 'penalty_hostage_incapped',
                        '7' : 'penalty_hostage_killed',
                        '8' : 'penalty_officer_incapped',
                        '9' : 'penalty_officer_injured',
                        '10': 'bonus_officer_alive',
                        '11': 'bonus_all_suspects_alive',
                        '12': 'penalty_deadly_force',
                        '13': 'penalty_force',
                        '14': 'bonus_officer_uninjured',
                        '15': 'penalty_evidence_destroyed',
                        '16': 'penalty_suspect_escaped',
                        '17': 'bonus_character_reported',
                        '18': 'bonus_evidence_secured',
                    },
                },
                '1': {
                    'type': node.StringPatternNode,
                    'name': 'status',
                    'required': False,
                    'default': '0',
                },
                '2': {
                    'type': node.NumericPatternNode,
                    'name': 'score',
                    'required': False,
                    'default': '0',
                },
            },
        },
    },
    # Player list
    '27': {
        'type': node.ListPatternNode,
        'name': 'players',
        'required': False,
        'item': {
            'type': node.DictPatternNode,
            'items': {
                '0': {
                    'type': node.NumericPatternNode,
                    'name': 'id',
                    'required': True,
                },
                '1': {
                    'type': node.StringPatternNode,
                    'name': 'ip',
                    'required': True,
                },
                '2': {
                    'type': node.BooleanPatternNode,
                    'name': 'dropped',
                    'required': False,
                    'default': '0',
                },
                '3': {
                    'type': node.BooleanPatternNode,
                    'name': 'admin',
                    'required': False,
                    'default': '0',
                },
                '4': {
                    'type': node.BooleanPatternNode,
                    'name': 'vip',
                    'required': False,
                    'default': '0',
                },
                '5': {
                    'type': node.StringPatternNode,
                    'name': 'name',
                    'required': True,
                },
                '6': {
                    'type': node.MappingPatternNode,
                    'name': 'team',
                    'required': False,
                    'default': '0',
                    'table': {
                        '0': 'swat',
                        '1': 'suspects',
                        '2': 'swat_red',  # CO-OP Team Red
                    },
                },
                '7': {
                    'type': node.NumericPatternNode,
                    'name': 'time',
                    'required': False,
                    'default': '0',
                },
                '8': {
                    'type': node.NumericPatternNode,
                    'name': 'score',
                    'required': False,
                    'default': '0',
                },
                '9': {
                    'type': node.NumericPatternNode,
                    'name': 'kills',
                    'required': False,
                    'default': '0',
                },
                '10': {
                    'type': node.NumericPatternNode,
                    'name': 'teamkills',
                    'required': False,
                    'default': '0',
                },
                '11': {
                    'type': node.NumericPatternNode,
                    'name': 'deaths',
                    'required': False,
                    'default': '0',
                },
                '12': {
                    'type': node.NumericPatternNode,
                    'name': 'suicides',
                    'required': False,
                    'default': '0',
                },
                '13': {
                    'type': node.NumericPatternNode,
                    'name': 'arrests',
                    'required': False,
                    'default': '0',
                },
                '14': {
                    'type': node.NumericPatternNode,
                    'name': 'arrested',
                    'required': False,
                    'default': '0',
                },
                '15': {
                    'type': node.NumericPatternNode,
                    'name': 'kill_streak',
                    'required': False,
                    'default': '0',
                },
                '16': {
                    'type': node.NumericPatternNode,
                    'name': 'arrest_streak',
                    'required': False,
                    'default': '0',
                },
                '17': {
                    'type': node.NumericPatternNode,
                    'name': 'death_streak',
                    'required': False,
                    'default': '0',
                },
                '18': {
                    'type': node.NumericPatternNode,
                    'name': 'vip_captures',
                    'required': False,
                    'default': '0',
                },
                '19': {
                    'type': node.NumericPatternNode,
                    'name': 'vip_rescues',
                    'required': False,
                    'default': '0',
                },
                '20': {
                    'type': node.NumericPatternNode,
                    'name': 'vip_escapes',
                    'required': False,
                    'default': '0',
                },
                '21': {
                    'type': node.NumericPatternNode,
                    'name': 'vip_kills_valid',
                    'required': False,
                    'default': '0',
                },
                '22': {
                    'type': node.NumericPatternNode,
                    'name': 'vip_kills_invalid',
                    'required': False,
                    'default': '0',
                },
                '23': {
                    'type': node.NumericPatternNode,
                    'name': 'rd_bombs_defused',
                    'required': False,
                    'default': '0',
                },
                '24': {
                    'type': node.NumericPatternNode,
                    'name': 'rd_crybaby',
                    'required': False,
                    'default': '0',
                },
                '25': {
                    'type': node.NumericPatternNode,
                    'name': 'sg_kills',
                    'required': False,
                    'default': '0',
                },
                '26': {
                    'type': node.NumericPatternNode,
                    'name': 'sg_escapes',
                    'required': False,
                    'default': '0',
                },
                '27': {
                    'type': node.NumericPatternNode,
                    'name': 'sg_crybaby',
                    'required': False,
                    'default': '0',
                },
                '28': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_hostage_arrests',
                    'required': False,
                    'default': '0',
                },
                '29': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_hostage_hits',
                    'required': False,
                    'default': '0',
                },
                '30': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_hostage_incaps',
                    'required': False,
                    'default': '0',
                },
                '31': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_hostage_kills',
                    'required': False,
                    'default': '0',
                },
                '32': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_enemy_arrests',
                    'required': False,
                    'default': '0',
                },
                '33': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_enemy_incaps',
                    'required': False,
                    'default': '0',
                },
                '34': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_enemy_kills',
                    'required': False,
                    'default': '0',
                },
                '35': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_enemy_incaps_invalid',
                    'required': False,
                    'default': '0',
                },
                '36': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_enemy_kills_invalid',
                    'required': False,
                    'default': '0',
                },
                '37': {
                    'type': node.NumericPatternNode,
                    'name': 'coop_toc_reports',
                    'required': False,
                    'default': '0',
                },
                # COOP status
                '38': {
                    'type': node.MappingPatternNode,
                    'name': 'coop_status',
                    'required': False,
                    'default': '0',
                    'table': {
                        '0': 'not_ready',
                        '1': 'ready',
                        '2': 'healthy',
                        '3': 'injured',
                        '4': 'incapacitated',
                    },
                },
                # Loadout
                '39': {
                    'type': node.DictPatternNode,
                    'name': 'loadout',
                    'required': False,
                    'items': {
                        # Primary weapon
                        '0': {
                            'type': node.MappingPatternNode,
                            'name' : 'primary',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Primary weapon ammo
                        '1': {
                            'type': node.MappingPatternNode,
                            'name' : 'primary_ammo',
                            'required': False,
                            'table': AMMO,
                            'default': '0',
                        },
                        # Secondary weapon
                        '2': {
                            'type': node.MappingPatternNode,
                            'name' : 'secondary',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Secondary weapon ammo
                        '3': {
                            'type': node.MappingPatternNode,
                            'name' : 'secondary_ammo',
                            'required': False,
                            'table': AMMO,
                            'default': '0',
                        },
                        # Equip slot #1
                        '4': {
                            'type': node.MappingPatternNode,
                            'name' : 'equip_one',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #2
                        '5': {
                            'type': node.MappingPatternNode,
                            'name' : 'equip_two',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #3
                        '6': {
                            'type': node.MappingPatternNode,
                            'name' : 'equip_three',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #4
                        '7': {
                            'type': node.MappingPatternNode,
                            'name' : 'equip_four',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #5
                        '8': {
                            'type': node.MappingPatternNode,
                            'name' : 'equip_five',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Breacher
                        '9': {
                            'type': node.MappingPatternNode,
                            'name' : 'breacher',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Body armor
                        '10': {
                            'type': node.MappingPatternNode,
                            'name' : 'body',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Head armor
                        '11': {
                            'type': node.MappingPatternNode,
                            'name' : 'head',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                    },
                },
                # Weapons
                '40': {
                    'type': node.ListPatternNode,
                    'name': 'weapons',
                    'required': False,
                    'item': {
                        'type': node.DictPatternNode,
                        'items': {
                            '0': {
                                'type': node.MappingPatternNode,
                                'name': 'name',
                                'required': True,
                                'table': EQUIPMENT,
                            },
                            '1': {
                                'type': node.NumericPatternNode,
                                'name' : 'time',
                                'required': False,
                                'default': '0',
                            },
                            '2': {
                                'type': node.NumericPatternNode,
                                'name' : 'shots',
                                'required': False,
                                'default': '0',
                            },
                            '3': {
                                'type': node.NumericPatternNode,
                                'name' : 'hits',
                                'required': False,
                                'default': '0',
                            },
                            '4': {
                                'type': node.NumericPatternNode,
                                'name' : 'teamhits',
                                'required': False,
                                'default': '0',
                            },
                            '5': {
                                'type': node.NumericPatternNode,
                                'name' : 'kills',
                                'required': False,
                                'default': '0',
                            },
                            '6': {
                                'type': node.NumericPatternNode,
                                'name' : 'teamkills',
                                'required': False,
                                'default': '0',
                            },
                            '7': {
                                'type': node.NumericPatternNode,
                                'name' : 'distance',
                                'required': False,
                                'default': '0',
                            },
                        },
                    }
                },
            },
        },
    },
}

# julia pattern for whois api 
WHOIS_PATTERN = {
    '0': {
        'type': node.StringPatternNode,
        'name': 'hash',
        'required': True,
    },
    '1': {
        'type': node.StringPatternNode,
        'name': 'command',
        'required': True,
    },
    '2': {
        'type': node.StringPatternNode,
        'name': 'command_id',
        'required': True,
    },
    '3': {
        'type': node.StringPatternNode,
        'name': 'args',
        'required': False,
        'default': '',
    },
}
