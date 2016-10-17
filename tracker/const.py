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
            '2': 'SAS',
            '3': 'SSF Realism Mod',
            '4': 'H.S.M.E',
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
            '-1': 'Unknown Map',
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

            # Custom maps (Thanks to ||ESA||RIddIK for all the hard work getting this list done)
            '24': 'Untitled',  # common name for all the "Unitled" maps
            '25': 'Fairfaxe Reloaded',  # SP-FAIRFAX-Reloaded.s4m
            '26': 'Final Crack Down, COOP',  # FinalCrackDown_COOP.s4m
            '27': 'ApartmentNew',  # SP-ApartmentNew.s4m
            '28': 'Saint-Paul Asylum',  # MP-Asylum.s4m, SP-St_Paul_Asylum_v1_0.s4m
            '29': '[c=ffff00]ESA\'s [c=1e90ff]Foodwall Edit',  # MP-ESA_FoodWall.s4m
            '30': 'La Mina v.1.5',  # MP-LA_MINA_15.s4m
            '31': 'Operation Apollo COOP 1.1 - FIX',  # SP-Apollo_COOP-FIX.s4m
            '32': 'Cave Complex',  # SP-CaveComplex.s4m
            '33': 'Predator2',  # SP-SWAT4Predator2.s4m
            '34': '{EP}Matt´s  Power Plant TSS',  # SP-EPpower-TSS.s4m
            '35': 'Qwik Fuel (Desrat\'s SAG)',  # MP-ConvenienceStore-smash2.s4m
            '36': 'Black Water-TTC 1.1',  # MP-BlackWater.s4m, SP-BlackWater.s4m
            '37': 'The Watercrip',  # The_Watercrip.s4m
            '38': '2940 Enemy Territory MP',  # MP-2940_Enemy_Territory.s4m
            '39': 'Newfort (Revision 24) TSS',  # SP-Newfort24-TSS.s4m
            '40': '-EXP- Drug Lab-RMX',  # SP-DrugLab-RMX.s4m
            '41': 'Riverside Training (Desrat\'s SAG)',  # MP-Training-smash2.s4m
            '42': 'The Building',  # SP-TheBuilding.s4m
            '43': 'Newfort (Revision 24)',  # SP-Newfort24.s4m
            '44': 'Wolcott (Desrat\'s SAG)',  # MP-ArmsDeal-smash2.s4m
            '45': 'Operation Apollo 1.1 - FIXED',  # MP-Apollo-FIX.s4m
            '46': 'Office Space V2.0',  # SP-OfficeSpacev2.s4m, MP-OfficeSpacev2.s4m
            '47': 'panic room',  # SP-Panic-Room.s4m
            '48': 'mistero18-byilmassacratore',  # Mistero18.s4m
            '49': 'The Phoenix Club',  # SP-PhoenixClub.s4m, MP-PhoenixClub.s4m
            '50': 'The Hive (VIP)',  # MP-Hive.s4m
            '51': 'U-273',  # MP-U273.s4m, SP-U273.s4m
            '52': 'The Manor - 1.1 - 2013',  # Sp-TheManor.s4m
            '53': '-EXP- Newfort (Revision 27)',  # SP-Newfort27EXP.s4m
            '54': 'City Streets 1.0',  # MP-CityStreets.s4m
            '55': 'LA City Hall',  # MP-City_Hall_VIP.s4m, MP-City_Hall.s4m, SP-City_Hall.s4m
            '56': '-MODv- California Security Bank - FIXED',  # MP-Bank-FIX.s4m, SP-Bank-FIX.s4m
            '57': 'Car\'s dealer v1.2',  # SP-CARsDEALER.s4m
            '58': 'Mout McKenna 1.0',  # MP-MoutMckenna.s4m, SP-MoutMckenna.s4m
            '59': 'Desert ops -Village- 1.0',  # SP-DesertOpsVillage.s4m, MP-DesertOpsVillage.s4m
            '60': 'INTERVAL - 17 - Rmx',  # SP-INTERVAL-17-rmx.s4m
            '61': 'Ashes and Ghosts -Night-',  # MP-Ashes_And_Ghosts_Night.s4m, SP-Ashes_And_Ghosts_Night.s4m
            '62': 'Penthouse',  # SP-Penthouse.s4m
            '63': 'Civil Unrest',  # MP-Civil_Unrest.s4m, SP-Civil_Unrest.s4m
            '64': 'Storm Front',  # SP-StormFront.s4m
            '65': 'Johnson Residence',  # SP-JohnsonResidence.s4m
            '66': 'Operation Prison Break',  # SP-Prison.s4m, MP-Prison.s4m
            '67': 'C-Block',  # MP-CBlock.s4m, MP-CBlock1_1.s4m
            '68': 'The Hive 1.1',  # SP-Hive1_1.s4m
            '69': 'BattleShips',  # BattleShips.s4m
            '70': 'Children of Taronne (Desrat\'s SAG)',  # MP-Tenement-smash2.s4m
            '71': 'Fast Break - Through',  # MP-FastBreak-Through.s4m
            '72': 'A-Bomb (Desrat\'s SAG)',  # MP-ABomb-smash2.s4m
            '73': 'Ashes and Ghosts -Day-',  # SP-Ashes_And_Ghosts_Day.s4m
            '74': 'ESA\'s 3or1',  # MP-ESA-3or1.s4m
            '75': 'MP-Terminal',  # MP-Terminal.s4m
            '76': 'The Entrepot',  # SP-Entrepot.s4m
            '77': 'E.T.E.R. Training Center',  # MP-Eter_trainingcenter.s4m
            '78': 'Subway Station v1.0',  # MP-Sub.s4m, SP-Sub.s4m
            '79': 'Stuck in the Woods',  # SP-StuckInTheWoods.s4m
            '80': '-EXP- Sisters of Mercy-RMX',  # SP-SistersofMercy-RMX.s4m
            '81': 'Research Center (Desrat\'s SAG)',  # MP-DNA-smash2.s4m
            '82': 'Brewer County (Desrat\'s SAG)',  # MP-Courthouse-smash2.s4m
            '83': 'Stuck in the woods',  # MP-StuckInTheWoods.s4m
            '84': '{EP}Matt´s Drugs Deal TSS',  # SP-EPdrugsdeal-TSS.s4m
            '85': 'Snake\'s loft',  # SP-Snake-loft.s4m
            '86': 'NewfortBeta',  # MP-NewfortBetaV2.s4m
            '87': 'BLUES CLUB',  # MP-BCv1.s4m
            '88': 'Fairfax Residence (Desrat\'s SAG)',  # MP-FairfaxResidence-smash2.s4m
            '89': 'Construction',  # SP-Construction.s4m, MP-Construction.s4m
            '90': 'Sky Tower',  # SP-SkyTower.s4m
            '91': 'Food Wall (Desrat\'s SAG)',  # MP-Foodwall-smash2.s4m
            '92': 'California Security Bank',  # SP-Bank.s4m
            '93': 'Dark Waters',  # MP-DarkWaters.s4m
            '94': 'Operation Apollo COOP 1.1',  # SP-Apollo_COOP.s4m
            '95': 'FAYA\'s REFUGEES v1.0',  # SP-FAYAsREFUGEES.s4m
            '96': 'Victory Imports (Desrat\'s SAG)',  # MP-AutoGarage-smash2.s4m
            '97': 'Residential Ops.',  # SP-ResidentialOps.s4m
            '98': '2940 Enemy Territory',  # SP-2940_Enemy_Territory.s4m
            '99': 'Clear - Room Service',  # MP-Clear.s4m
            '100': 'Tantive IV',  # MP-TantiveIV.s4m
            '101': 'Red Library (Desrat\'s SAG)',  # MP-RedLibrary-smash2.s4m
            '102': 'Dark Scarlet Restaurant',  # SP-Dark_Scarlet.s4m
            '103': 'LA MINA',  # MP-LA_MINA.s4m
            '104': 'Precinct HQ 1.1',  # SP-PrecinctHQ.s4m, MP-PrecinctHQ.s4m
            '105': 'Novatech\'s Building',  # SP-NOVATECHsBUILDING.s4m
            '106': 'Mout McKenna Snow 1.0',  # MP-MoutMckennaSnow.s4m, SP-MoutMckennaSnow.s4m
            '107': '(SEALMAP)Desert_Dust',  # MP-Desert_Dust.s4m, SP-Desert_Dust.s4m, MP2-Desert_Dust.s4m
            '108': 'Mogadishu Mile 1.0',  # MP-DesertOps2.s4m
            '109': 'ATL Convention Center',  # MP-ATLConvention.s4m
            '110': 'Gangster_Hangout',  # MP-GangsterHangout.s4m
            '111': '(SEALMAP)Renovate TSS',  # SP-Renovate-TSS.s4m
            '112': 'Brentwood Reloaded',  # SP-BrentReloaded.s4m, MP-BrentReloaded.s4m
            '113': 'Operation Apollo 1.1',  # MP-Apollo.s4m, SP-Apollo.s4m
            '114': 'The China Hotel',  # SP-CHINA-HOTEL.s4m
            '115': 'Mad Shopping',  # SP-MadShopping.s4m, MP-MadShopping.s4m
            '116': '(SEALMAP)School',  # SP-School.s4m, MP-School.s4m
            '117': 'Diamond Center (Desrat\'s SAG)',  # MP-JewelryHeist-smash2.s4m
            '118': 'Newfort2xSus',  # SP-Newfort100Sus.s4m
            '119': 'Ocean Avenue 112',  # MP-Amityville_Horror_VIP.s4m, SP-Amityville_Horror.s4m, MP-Amityville_Horror.s4m
            '120': '|ustt| Enemy Territory V2',  # MP-USTT_Enemy_Territory2.s4m
            '121': 'Project -SERO- 1.0',  # MP-ProjectSero.s4m, SP-ProjectSero.s4m
            '122': 'C-Block Taronne is back',  # SP-CBlock.s4m
            '123': 'Reality Simulation Logistic V1.0',  # MP-Spedition.s4m
            '124': 'Power Plant (Desrat\'s SAG)',  # MP-PowerPlant-smash2.s4m
            '125': '5455, Carlton Way',  # SP-Getts.s4m, MP-Getts.s4m
            '126': 'Assault On City Hall',  # SP-CityHall.s4m, MP-CityHall.s4m
            '127': 'Fy_Iceworld2005',  # MP_Fy_iceworld2005.s4m
            '128': 'Art Center 1.0',  # SP-ArtCenter.s4m, MP-ArtCenter.s4m
            '129': 'Wainwright Offices',  # SP-Wainwright_Offices.s4m, MP-Wainwright_Offices.s4m
            '130': 'Children of Tenement-RMX',  # SP-Tenement-RMX.s4m
            '131': 'Police Station 1.0 - 2013',  # SP-PoliceStation.s4m
            '132': 'Hotel Carlyle 2005 v.2.0',  # SP-Carlyle2k5v2-0.s4m
            '133': 'The Asylum',  # SP-TheAsylum.s4m
            '134': 'Final Crack Down, Barricaded Suspects',  # FinalCrackDown_BARR.s4m
            '135': 'New Library 1.0',  # SP-NewLibrary.s4m
            '136': 'Star Wars',  # SP-StarWars.s4m
            '137': '-MODv- Johnson Residence - FIXED',  # SP-JohnsonResidence-FIX.s4m
            '138': '-MODv- Hotel Carlyle 2005 - FIXED',  # SP-Carlyle2k5-FIX.s4m
            '139': 'Old Granite Hotel (Desrat\'s SAG)',  # MP-Hotel-smash2.s4m
            '140': 'Section 8 Fairfax Massacre',  # MP-Massacre.s4m, SP-Massacre.s4m
            '141': 'Club ATL',  # SP-ClubATL.s4m
            '142': 'DELTA CENTER',  # SP-DELTA-CENTER.s4m
            '143': 'Mittelplate Alpha 1.1',  # MP-Mittelplate_Alpha.s4m
            '144': 'panic room Coop',  # SP-PANIC-ROOM-Coop.s4m
            '145': 'Mittelplate Alpha 1.2',  # SP-Mittelplate_Alpha.s4m
            '146': 'Residential Ops VIP',  # MP-ResidentialOps.s4m
            '147': 'Nova Corp.',  # SP-Nova-Corp.s4m
            '148': 'Flash Light Tag',  # MP-FlashLightTag.s4m
            '149': 'Mad Butcher`s Shop',  # SP-MadButcher.s4m
            '150': 'CREEPY HOTEL',  # SP-CREEPY-HOTEL.s4m
            '151': 'SSF Night Rescue',  # SSFNightRescue.s4m
            '152': 'Operation Prison Break TSS',  # SP-Prison-TSS.s4m
            '153': 'Terminal',  # SP-Terminal.s4m
            '154': 'Paintball Madness',  # MP-PaintballMadness.s4m
            '155': 'Madmap',  # MP-Madmap.s4m, SP-Madmap.s4m
            '156': '[c=ffff00]ESA\'s [c=1e90ff]Riverside Edit',  # MP-ESA_Training.s4m
            '157': 'The Baths Of Anubis',  # SP-BATHS-Of-ANUBIS.s4m
            '158': 'DEAD_END',  # SP-DEAD_END.s4m, MP-DEAD_END.s4m
            '159': 'KEOWAREHOUSE',  # SP-KEOWAREHOUSE.s4m
            '160': 'DeAdMaNs UsEd CaR LoT',  # MP-UsedCarLot.s4m, SP-UsedCarLot.s4m
            '161': 'Ventura Hotel',  # SP-Ventura.s4m, MP-Ventura.s4m
            '162': 'SP-UNDERGROUND',  # SP-UNDERGROUND.s4m
            '163': 'Medical Center (Desrat\'s SAG)',  # MP-Hospital-smash2.s4m
            '164': 'The Metropol',  # SP-Metropol.s4m
            '165': 'MP-Le Camp',  # Mp-LeCamp.s4m
            '166': 'SubWay',  # SP-Last-Stop.s4m
            '167': 'The Killing House -Small-',  # MP-KillingHouseSmall.s4m
            '168': 'Reaction: Ak/Colt',  # MP-Reaction_ak_colt.s4m
            '169': '=HT=Operation Freedom',  # MP-opfreedom.s4m
            '170': 'Genovese & Feinbloom',  # MP-Genovese&Feinbloom.s4m, SP-Genovese&Feinbloom.s4m
            '171': '|ustt| Enemy Territory V2 CoOp',  # SP-USTT_Enemy_Territory2.s4m
            '172': 'The Building v1.1',  # SP-TheBuilding-v1_1.s4m
            '173': 'AssasinationRoom, Aupicia:Clan A-T',  # MP-AssasinationRoom.s4m
            '174': 'Department Of Criminal Justice V1',  # MP-DOCJT.s4m, SP-DOCJT.s4m
            '175': 'Combat Zone',  # MP-CombatZone.s4m, SP-CombatZone.s4m
            '176': 'Ventura Hotel v1r1',  # MP-ESA-Venturav1r1.s4m
            '177': '{EP}Matt´s Medical Center TSS',  # SP-EPhosp-TSS.s4m
            '178': 'SSF TrainingCenter 1.0',  # MP-Trainingcenter.s4m
            '179': 'Operation Dusk Till Dawn',  # SP-Dusk.s4m
            '180': 'MP Rush',  # MP-Rush.s4m
            '181': 'SP-TRANSPORT',  # SP-TRANSPORT.s4m
            '182': 'Parking Garage v1.0',  # MP-ParkingGarage.s4m
            '183': 'Club -[*ATL*]-',  # MP-ClubATL.s4m
            '184': 'TERRORISTA',  # SP-Terrorista.s4m
            '185': 'Meat Barn (Desrat\'s SAG)',  # MP-MeatBarn-smash2.s4m
            '186': 'Gris Import Export',  # SP-Import.s4m
            '187': 'The Cinepark Conflict',  # SP-CineparkConflict.s4m
            '188': 'Cabin Fever',  # SP-CabinFever.s4m
            '189': 'Swanky Mansion',  # SP-SwankyMansion.s4m
            '190': 'Apartment 525',  # SP-Apartment525.s4m
            '191': 'Warehouse 5th Street',  # MP-Warehouse5thStreet.s4m, SP-Warehouse5thStreet.s4m
            '192': 'Operation DayBreak',  # MP-DayBreak.s4m, SP-DayBreak.s4m
            '193': 'Brewer County Courthouse COOP',  # SP-Courthouse.s4m
            '194': 'Food Wall Restaurant butchered',  # MP-Foodwall2.s4m
            '195': 'Fede\'s Nightmare',  # MP-FedesNightmare.s4m
            '196': '(SEALMAP)Central_Base',  # MP-Central_Base.s4m, SP-Central_Base.s4m
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
                            'name': 'primary',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Primary weapon ammo
                        '1': {
                            'type': node.MappingPatternNode,
                            'name': 'primary_ammo',
                            'required': False,
                            'table': AMMO,
                            'default': '0',
                        },
                        # Secondary weapon
                        '2': {
                            'type': node.MappingPatternNode,
                            'name': 'secondary',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Secondary weapon ammo
                        '3': {
                            'type': node.MappingPatternNode,
                            'name': 'secondary_ammo',
                            'required': False,
                            'table': AMMO,
                            'default': '0',
                        },
                        # Equip slot #1
                        '4': {
                            'type': node.MappingPatternNode,
                            'name': 'equip_one',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #2
                        '5': {
                            'type': node.MappingPatternNode,
                            'name': 'equip_two',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #3
                        '6': {
                            'type': node.MappingPatternNode,
                            'name': 'equip_three',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #4
                        '7': {
                            'type': node.MappingPatternNode,
                            'name': 'equip_four',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Equip slot #5
                        '8': {
                            'type': node.MappingPatternNode,
                            'name': 'equip_five',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Breacher
                        '9': {
                            'type': node.MappingPatternNode,
                            'name': 'breacher',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Body armor
                        '10': {
                            'type': node.MappingPatternNode,
                            'name': 'body',
                            'required': False,
                            'table': EQUIPMENT,
                            'default': '0',
                        },
                        # Head armor
                        '11': {
                            'type': node.MappingPatternNode,
                            'name': 'head',
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
                                'name': 'time',
                                'required': False,
                                'default': '0',
                            },
                            '2': {
                                'type': node.NumericPatternNode,
                                'name': 'shots',
                                'required': False,
                                'default': '0',
                            },
                            '3': {
                                'type': node.NumericPatternNode,
                                'name': 'hits',
                                'required': False,
                                'default': '0',
                            },
                            '4': {
                                'type': node.NumericPatternNode,
                                'name': 'teamhits',
                                'required': False,
                                'default': '0',
                            },
                            '5': {
                                'type': node.NumericPatternNode,
                                'name': 'kills',
                                'required': False,
                                'default': '0',
                            },
                            '6': {
                                'type': node.NumericPatternNode,
                                'name': 'teamkills',
                                'required': False,
                                'default': '0',
                            },
                            '7': {
                                'type': node.NumericPatternNode,
                                'name': 'distance',
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
    '4': {
        'type': node.StringPatternNode,
        'name': 'player_name',
        'required': False,
        'default': '',
    },
    '5': {
        'type': node.StringPatternNode,
        'name': 'player_ip',
        'required': False,
        'default': '',
    },
}
