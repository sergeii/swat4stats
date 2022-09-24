from voluptuous import Schema, Optional, All, In, Coerce, Range, Boolean, REMOVE_EXTRA, Maybe

from apps.utils.schema import Mapping, FallbackMapping, OptionalMapping, DefaultMapping


teams_encoded = {
    0: 'swat',
    1: 'suspects',
    2: 'swat',  # CO-OP Team Red
}

teams_reversed = {
    'swat': 0,
    'suspects': 1,
}

coop_status_encoded = {
    0: None,
    1: 'Ready',
    2: 'Healthy',
    3: 'Injured',
    4: 'Incapacitated',
}

coop_status_reversed = {
    coop_status_code: coop_status_int
    for coop_status_int, coop_status_code in coop_status_encoded.items()
}

gametypes_encoded = {
    '0': 'Barricaded Suspects',
    '1': 'VIP Escort',
    '2': 'Rapid Deployment',
    '3': 'CO-OP',
    '4': 'Smash And Grab',
    '5': 'CO-OP QMM',
}

gametypes_reversed = {
    gametype_code: int(gametype_int)
    for gametype_int, gametype_code in gametypes_encoded.items()
}

gamenames_encoded = {
    '0': 'SWAT 4',
    '1': 'SWAT 4X',
}

mapnames_encoded = {
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
}

mapnames_reversed = {
    map_name: map_legacy_id
    for map_legacy_id, map_name in mapnames_encoded.items()
}

outcome_encoded = {
    0: None,
    1: 'swat_bs',             # SWAT victory in Barricaded Suspects
    2: 'sus_bs',              # Suspects victory in Barricaded Suspects
    3: 'swat_rd',             # SWAT victory in Rapid Deployment (all bombs have been exploded)
    4: 'sus_rd',              # Suspects victory in Rapid Deployment (all bombs have been deactivated)
    5: 'tie',                 # A tie
    6: 'swat_vip_escape',     # SWAT victory in VIP Escort - The VIP has escaped
    7: 'sus_vip_good_kill',   # Suspects victory in VIP Escort - Suspects have executed the VIP
    8: 'swat_vip_bad_kill',   # SWAT victory in VIP Escort - Suspects have killed the VIP
    9: 'sus_vip_bad_kill',    # Suspects victory in VIP Escort - SWAT have killed the VIP
    10: 'coop_completed',     # COOP objectives have been completed
    11: 'coop_failed',        # COOP objectives have been failed
    12: 'swat_sg',            # SWAT victory in Smash and Grab
    13: 'sus_sg',             # Suspects victory in Smash and Grab
}

outcome_reversed = {
    outcome_code: outcome_int
    for outcome_int, outcome_code in outcome_encoded.items()
}

objectives_encoded = {
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

objectives_reversed = {
    objective_code: objective_int
    for objective_int, objective_code in objectives_encoded.items()
}

objective_mapping = {
    'Arrest_Jennings': 'Rendezvous with Jennings',
    'Custom_NoCiviliansInjured': 'Avoid civilian injuries',
    'Neutralize_Alice': 'Neutralize Alice Jenkins',
    'Neutralize_All_Enemies': 'Bring order to chaos',
    'Neutralize_Arias': 'Neutralize Javier Arias',
    'Neutralize_CultLeader': 'Neutralize Andrew Taronne',
    'Neutralize_Georgiev': 'Neutralize Anton Georgiev',
    'Neutralize_Grover': 'Neutralize Simon Gowan',
    'Neutralize_GunBroker': 'Neutralize Lian Niu',
    'Neutralize_Jimenez': 'Neutralize Alex Jimenez',
    'Neutralize_Killer': 'Neutralize Lawrence Fairfax',
    'Neutralize_Kiril': 'Neutralize Kiril Stetchkov',
    'Custom_NoOfficersInjured': 'Avoid officer injuries',
    'Neutralize_Koshka': 'Neutralize Hadeon Koshka',
    'Neutralize_Kruse': 'Neutralize Allen Kruse',
    'Neutralize_Norman': 'Neutralize Andrew Norman',
    'Neutralize_TerrorLeader': 'Neutralize Jean Trouffant',
    'Neutralize_Todor': 'Neutralize Todor Stetchkov',
    'Rescue_Adams': 'Rescue Lawrence Adams',
    'Rescue_All_Hostages': 'Rescue all of the civilians',
    'Rescue_Altman': 'Rescue Gary Altman',
    'Rescue_Baccus': 'Arrest Louie Baccus',
    'Rescue_Bettencourt': 'Rescue James Betincourt',
    'Custom_NoOfficersKilled': 'Avoid officer casualties',
    'Rescue_Bogard': 'Rescue Oscar Bogard',
    'Rescue_CEO': 'Rescue Warren Rooney',
    'Rescue_Diplomat': 'Rescue Hyun-Jun Park',
    'Rescue_Fillinger': 'Rescue Willis Fischer',
    'Rescue_Kline': 'Rescue Melinda Kline',
    'Rescue_Macarthur': 'Rescue Lionel Macarthur',
    'Rescue_Rosenstein': 'Rescue Heidi Rosenstein',
    'Rescue_Sterling': 'Rescue Dr. Theodore Sturgeon',
    'Rescue_Victims': 'Rescue Kim Dong Yin',
    'Rescue_Walsh': 'Rescue Detective Walsh',
    'Custom_NoSuspectsKilled': 'Avoid suspect casualties',
    'Rescue_Wilkins': 'Locate Officer Wilkins',
    'Rescue_Winston': 'Rescue Rita Winston',
    'Secure_Briefcase': 'Secure the briefcase',
    'Secure_Weapon': 'Secure the MAC-10',
    'Custom_PlayerUninjured': 'Avoid injuries to yourself',
    'Custom_Timed': 'Debrief before the timer expires',
    'Disable_Bombs': 'Find and deactivate the bombs',
    'Disable_Office_Bombs': 'Find and disarm the bombs!',
    'Investigate_Laundromat': 'Investigate the laundromat',
    # SEF
    'BangAndClear': 'Order the element to Bang and Clear',
    'BlueStackUp': 'Order the Blue Team to Stack Up',
    'CommandThroughViewport': 'Order Blue to Move & Clear using viewport',
    'Complete_GrenadePractice': 'Try each of the grenades',
    'Complete_LockedDoors': 'Get through the locked doors',
    'Complete_ShootingRange': 'Fire your weapons at all three distances',
    'Complete_TargetPractice': 'Shoot each of the four targets',
    'Complete_Training': 'Complete the training course',
    'FirstDefault': 'Order the element to Fall In',
    'Keep_Cadets_Healthy': 'Do not incapacitate the volunteers',
    'Keep_Trainer_Alive': 'Do not kill Lieutenant Bonds',
    'Keep_Volunteers_Alive': 'Do not kill the volunteers',
    'MoveRedToOtherDoor': 'Bring Red to the door on the left',
    'Neutralize_Moretti': 'Neutralize Adam Moretti',
    'OpenAndClearDefault': 'Order the element to Open and Clear',
    'Rescue_Hanson': 'Do not kill Officer Hanson',
    'Rescue_Hostages': 'Rescue as many civilians as possible',
    'RestrainHanson': 'Restrain Officer Hanson',
    'Training_ProtectOfficers': 'Do not kill your fellow officers',
    'UseOptiwand': 'Order the element to Move and Clear',
    'UseSniper': 'Shoot the target with the sniper',
    'YellCompliance': 'Get Officer Hanson to comply'
}

objective_status_encoded = {
    0: 'In Progress',
    1: 'Completed',
    2: 'Failed',
}

objective_status_reversed = {
    objective_status_code: objective_status_int
    for objective_status_int, objective_status_code in objective_status_encoded.items()
}

procedures_encoded = {
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

procedures_reversed = {
    procedure_code: procedure_int
    for procedure_int, procedure_code in procedures_encoded.items()
}

equipment_encoded = {
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

equipment_reversed = {
    equipment_code: equipment_int
    for equipment_int, equipment_code in equipment_encoded.items()
}

ammo_encoded = {
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

ammo_reversed = {
    ammo_code: ammo_int
    for ammo_int, ammo_code in ammo_encoded.items()
}

weapon_encoded = {
    key: name for (key, name)
    in equipment_encoded.items()
    if key > 0
}

weapon_reversed = {
    weapon_code: weapon_int
    for weapon_int, weapon_code in weapon_encoded.items()
}


def extract_names(encoded_names):
    return [name for _, name in sorted(encoded_names.items(), key=lambda item: int(item[0]))]


gametype_names = extract_names(gametypes_encoded)
gamename_names = extract_names(gamenames_encoded)
mapname_names = extract_names(mapnames_encoded)
outcome_names = extract_names(outcome_encoded)

Int = Coerce(int)
String = Coerce(str)
PositiveInt = All(Int, Range(0))
BooleanInt = All(Boolean(), Int, Range(0, 1))
PositiveIntOrNone = All(Int, Coerce(lambda num: num if num > 0 else None))

LoadoutEquipment = All(Int, Mapping(equipment_encoded))
LoadoutAmmo = All(Int, Mapping(ammo_encoded))


class ListOrDict:
    """
    Allow a list schema to be used for both lists and enumerated dicts.
    """

    def __init__(self, schema):
        self.schema = Schema(schema, required=True, extra=REMOVE_EXTRA)

    def __call__(self, value):
        if isinstance(value, dict):
            value = list(value.values())
        return self.schema(value)


game_schema = Schema({
    # Unique identifier for this particular data set
    Mapping({'0': 'tag'}): str,
    # Mod version
    Mapping({'1': 'version'}): str,
    # Join port number
    Mapping({'2': 'port'}): All(Int, Range(1, 65535)),
    # Server time in the format of Unix Timestamp
    # The server declares itself to be in UTC timezone, which makes this value untrustworthy
    # On the other hand this is an excellent argument value for hashing
    Mapping({'3': 'timestamp'}): PositiveInt,
    # Last 32 bits of an md5 encoded request signature hash
    # The original hash is a product of the following parameters:
    # `server key` + `join port` + `timestamp`
    Mapping({'4': 'hash'}): str,
    # support old integer codes along with string titles
    OptionalMapping({'5': 'gamename'},
                    default='SWAT 4'): All(String,
                                           FallbackMapping(gamenames_encoded),
                                           In(gamename_names)),  # backward compat with encoded gamenames
    Mapping({'6': 'gamever'}): str,
    Mapping({'7': 'hostname'}): str,
    OptionalMapping({'8': 'gametype'},
                    default='Barricaded Suspects'): All(String,
                                                        FallbackMapping(gametypes_encoded),
                                                        In(gametype_names)),  # backward compat with encoded gametypes
    # support both old map numeric codes and pure map titles
    OptionalMapping({'9': 'mapname'},
                    default='A-Bomb Nightclub'): All(String, FallbackMapping(mapnames_encoded)),
    Optional(Mapping({'10': 'passworded'})): Boolean(),
    Mapping({'11': 'player_num'}): PositiveInt,
    Mapping({'12': 'player_max'}): PositiveInt,
    OptionalMapping({'13': 'round_num'}, default=0): PositiveInt,
    Mapping({'14': 'round_max'}): PositiveInt,
    # Time elapsed since the round start
    Mapping({'15': 'time_absolute'}): PositiveInt,
    # Time the game has actually span
    Mapping({'16': 'time'}): PositiveInt,
    # Round time limit
    Mapping({'17': 'time_limit'}): PositiveInt,
    OptionalMapping({'18': 'vict_swat'}, default=0): PositiveInt,
    OptionalMapping({'19': 'vict_sus'}, default=0): PositiveInt,
    OptionalMapping({'20': 'score_swat'}, default=0): Int,
    OptionalMapping({'21': 'score_sus'}, default=0): Int,
    Mapping({'22': 'outcome'}): All(Int, Mapping(outcome_encoded)),
    OptionalMapping({'23': 'bombs_defused'}, default=0): PositiveInt,
    OptionalMapping({'24': 'bombs_total'}, default=0): PositiveInt,
    Optional(Mapping({'25': 'coop_objectives'})): ListOrDict([{
        Mapping({'0': 'name'}): All(Int, Mapping(objectives_encoded)),
        OptionalMapping({'1': 'status'}, default=0): All(Int, Mapping(objective_status_encoded)),
    }]),
    Optional(Mapping({'26': 'coop_procedures'})): ListOrDict([{
        Mapping({'0': 'name'}): All(Int, Mapping(procedures_encoded)),
        OptionalMapping({'1': 'status'}, default='0'): str,
        OptionalMapping({'2': 'score'}, default=0): Int,
    }]),
    Optional(Mapping({'27': 'players'})): ListOrDict([{
        Mapping({'0': 'id'}): Int,
        Mapping({'1': 'ip'}): String,
        OptionalMapping({'2': 'dropped'}, default=False): Boolean(),
        OptionalMapping({'3': 'admin'}, default=False): Boolean(),
        Optional(Mapping({'4': 'vip'})): Boolean(),
        Mapping({'5': 'name'}): String,
        OptionalMapping({'6': 'team'}, default=0): All(Int, Mapping(teams_encoded)),
        Optional(Mapping({'7': 'time'})): PositiveInt,
        Optional(Mapping({'8': 'score'})): Int,
        Optional(Mapping({'9': 'kills'})): PositiveInt,
        Optional(Mapping({'10': 'teamkills'})): PositiveInt,
        Optional(Mapping({'11': 'deaths'})): PositiveInt,
        Optional(Mapping({'12': 'suicides'})): PositiveInt,
        Optional(Mapping({'13': 'arrests'})): PositiveInt,
        Optional(Mapping({'14': 'arrested'})): PositiveInt,
        Optional(Mapping({'15': 'kill_streak'})): PositiveInt,
        Optional(Mapping({'16': 'arrest_streak'})): PositiveInt,
        Optional(Mapping({'17': 'death_streak'})): PositiveInt,
        Optional(Mapping({'18': 'vip_captures'})): PositiveInt,
        Optional(Mapping({'19': 'vip_rescues'})): PositiveInt,
        Optional(Mapping({'20': 'vip_escapes'})): PositiveInt,
        Optional(Mapping({'21': 'vip_kills_valid'})): PositiveInt,
        Optional(Mapping({'22': 'vip_kills_invalid'})): PositiveInt,
        Optional(Mapping({'23': 'rd_bombs_defused'})): PositiveInt,
        Optional(Mapping({'24': 'rd_crybaby'})): PositiveInt,
        Optional(Mapping({'25': 'sg_kills'})): PositiveInt,
        Optional(Mapping({'26': 'sg_escapes'})): PositiveInt,
        Optional(Mapping({'27': 'sg_crybaby'})): PositiveInt,
        Optional(Mapping({'28': 'coop_hostage_arrests'})): PositiveInt,
        Optional(Mapping({'29': 'coop_hostage_hits'})): PositiveInt,
        Optional(Mapping({'30': 'coop_hostage_incaps'})): PositiveInt,
        Optional(Mapping({'31': 'coop_hostage_kills'})): PositiveInt,
        Optional(Mapping({'32': 'coop_enemy_arrests'})): PositiveInt,
        Optional(Mapping({'33': 'coop_enemy_incaps'})): PositiveInt,
        Optional(Mapping({'34': 'coop_enemy_kills'})): PositiveInt,
        Optional(Mapping({'35': 'coop_enemy_incaps_invalid'})): PositiveInt,
        Optional(Mapping({'36': 'coop_enemy_kills_invalid'})): PositiveInt,
        Optional(Mapping({'37': 'coop_toc_reports'})): PositiveInt,
        Optional(Mapping({'38': 'coop_status'})): All(Int, Mapping(coop_status_encoded)),
        Optional(Mapping({'39': 'loadout'})): {
            OptionalMapping({'0': 'primary'}, default=0): LoadoutEquipment,
            OptionalMapping({'1': 'primary_ammo'}, default=0): LoadoutAmmo,
            OptionalMapping({'2': 'secondary'}, default=0): LoadoutEquipment,
            OptionalMapping({'3': 'secondary_ammo'}, default=0): LoadoutAmmo,
            OptionalMapping({'4': 'equip_one'}, default=0): LoadoutEquipment,
            OptionalMapping({'5': 'equip_two'}, default=0): LoadoutEquipment,
            OptionalMapping({'6': 'equip_three'}, default=0): LoadoutEquipment,
            OptionalMapping({'7': 'equip_four'}, default=0): LoadoutEquipment,
            OptionalMapping({'8': 'equip_five'}, default=0): LoadoutEquipment,
            OptionalMapping({'9': 'breacher'}, default=0): LoadoutEquipment,
            OptionalMapping({'10': 'body'}, default=0): LoadoutEquipment,
            OptionalMapping({'11': 'head'}, default=0): LoadoutEquipment,
        },
        Optional(Mapping({'40': 'weapons'})): ListOrDict([{
            Mapping({'0': 'name'}): All(Int, DefaultMapping(weapon_encoded, default=-1)),
            OptionalMapping({'1': 'time'}, default=0): PositiveInt,
            OptionalMapping({'2': 'shots'}, default=0): PositiveInt,
            OptionalMapping({'3': 'hits'}, default=0): PositiveInt,
            OptionalMapping({'4': 'teamhits'}, default=0): PositiveInt,
            OptionalMapping({'5': 'kills'}, default=0): PositiveInt,
            OptionalMapping({'6': 'teamkills'}, default=0): PositiveInt,
            OptionalMapping({'7': 'distance'}, default=0): PositiveInt,
        }])
    }]),
}, required=True)


whois_schema = Schema({
    Mapping({'0': 'hash'}): str,
    Mapping({'1': 'command'}): str,
    Mapping({'2': 'command_id'}): str,
    Optional(Mapping({'3': 'args'})): str,
}, required=True)


serverquery_schema = Schema({
    'hostname': str,
    'hostport': PositiveInt,
    'gamevariant': str,
    'gamever': str,
    'gametype': str,
    'numplayers': PositiveInt,
    'maxplayers': PositiveInt,
    'mapname': str,
    'password': BooleanInt,
    Optional('statsenabled', default=0): BooleanInt,
    Optional('round', default=None): Maybe(PositiveInt),
    Optional('numrounds', default=None): Maybe(PositiveInt),
    Optional('timeleft', default=None): Maybe(PositiveIntOrNone),
    Optional('timespecial', default=None): Maybe(PositiveIntOrNone),
    Optional('swatscore', default=None): Maybe(Int),
    Optional('suspectsscore', default=None): Maybe(Int),
    Optional('swatwon', default=None): Maybe(PositiveInt),
    Optional('suspectswon', default=None): Maybe(PositiveInt),
    Optional('bombsdefused', default=None): Maybe(PositiveInt),
    Optional('bombstotal', default=None): Maybe(PositiveInt),
    Optional('tocreports', default=None): Maybe(str),
    Optional('weaponssecured', default=None): Maybe(str),
    'players': [{
        'id': Int,
        Mapping({'player': 'name'}): str,
        'ping': Int,
        Optional('score', default=0): Int,
        Optional('team', default=0): All(Int, Mapping(teams_encoded)),
        Optional('vip', default=0): BooleanInt,
        Optional('coopstatus', default=0): All(Int, Mapping(coop_status_encoded)),
        Optional('kills', default=0): PositiveInt,
        Optional('tkills', default=0): PositiveInt,
        Optional('deaths', default=0): PositiveInt,
        Optional('arrests', default=0): PositiveInt,
        Optional('arrested', default=0): PositiveInt,
        Optional('vescaped', default=0): PositiveInt,
        Optional('arrestedvip', default=0): PositiveInt,
        Optional('unarrestedvip', default=0): PositiveInt,
        Optional('validvipkills', default=0): PositiveInt,
        Optional('invalidvipkills', default=0): PositiveInt,
        Optional('bombsdiffused', default=0): PositiveInt,
        Optional('rdcrybaby', default=0): PositiveInt,
        Optional('sgcrybaby', default=0): PositiveInt,
        Optional('escapedcase', default=0): PositiveInt,
        Optional('killedcase', default=0): PositiveInt,
    }],
    'objectives': [{
        'name': Mapping(objective_mapping),
        'status': All(Int, Mapping(objective_status_encoded)),
    }]
}, required=True, extra=REMOVE_EXTRA)
