from enum import StrEnum, auto


class Team(StrEnum):
    swat = 'swat'
    suspects = 'suspects'


class GameType(StrEnum):
    barricaded_suspects = 'Barricaded Suspects'
    vip_escort = 'VIP Escort'
    rapid_deployment = 'Rapid Deployment'
    smash_and_grab = 'Smash And Grab'
    co_op = 'CO-OP'
    co_op_qmm = 'CO-OP QMM'

    @classmethod
    def versus_modes(cls) -> tuple['GameType', ...]:
        return cls.barricaded_suspects, cls.rapid_deployment, cls.vip_escort, cls.smash_and_grab


class GameName(StrEnum):
    swat4 = 'SWAT 4'
    swat4x = 'SWAT 4X'


class CoopStatus(StrEnum):
    ready = 'Ready'
    healthy = 'Healthy'
    injured = 'Injured'
    incapacitated = 'Incapacitated'


class CoopObjectiveStatus(StrEnum):
    in_progress = 'In Progress'
    completed = 'Completed'
    failed = 'Failed'


class CoopProcedure(StrEnum):
    suspects_incapacitated = 'Suspects incapacitated'
    suspects_arrested = 'Suspects arrested'
    mission_completed = 'Mission completed'
    failed_to_report_downed_officer = 'Failed to report a downed officer'
    suspects_neutralized = 'Suspects neutralized'
    no_civilians_injured = 'No civilians injured'
    incapacitated_hostage = 'Incapacitated a hostage'
    killed_hostage = 'Killed a hostage'
    incapacitated_fellow_officer = 'Incapacitated a fellow officer'
    injured_fellow_officer = 'Injured a fellow officer'
    no_officers_down = 'No officers down'
    no_suspects_neutralized = 'No suspects neutralized'
    unauthorized_use_of_deadly_force = 'Unauthorized use of deadly force'
    unauthorized_use_of_force = 'Unauthorized use of force'
    player_uninjured = 'Player uninjured'
    failed_to_prevent_destruction_of_evidence = 'Failed to prevent destruction of evidence.'
    failed_to_apprehend_fleeing_suspect = 'Failed to apprehend fleeing suspect.'
    report_status_to_toc = 'Report status to TOC'
    all_evidence_secured = 'All evidence secured'


class GameOutcome(StrEnum):
    swat_bs = auto()            # SWAT victory in Barricaded Suspects
    sus_bs = auto()             # Suspects victory in Barricaded Suspects
    swat_rd = auto()            # SWAT victory in Rapid Deployment (all bombs have been exploded)
    sus_rd = auto()             # Suspects victory in Rapid Deployment (all bombs have been deactivated)
    tie = auto()                # A tie
    swat_vip_escape = auto()    # SWAT victory in VIP Escort - The VIP has escaped
    sus_vip_good_kill = auto()  # Suspects victory in VIP Escort - Suspects have executed the VIP
    swat_vip_bad_kill = auto()  # SWAT victory in VIP Escort - Suspects have killed the VIP
    sus_vip_bad_kill = auto()   # Suspects victory in VIP Escort - SWAT have killed the VIP
    coop_completed = auto()     # COOP objectives have been completed
    coop_failed = auto()        # COOP objectives have been failed
    swat_sg = auto()            # SWAT victory in Smash and Grab
    sus_sg = auto()             # Suspects victory in Smash and Grab

    @classmethod
    def swat_victories(cls) -> tuple['GameOutcome', ...]:
        return cls.swat_bs, cls.swat_rd, cls.swat_vip_escape, cls.swat_vip_bad_kill, cls.swat_sg

    @classmethod
    def sus_victories(cls) -> tuple['GameOutcome', ...]:
        return cls.sus_bs, cls.sus_rd, cls.sus_vip_good_kill, cls.sus_vip_bad_kill, cls.sus_sg


class Equipment(StrEnum):
    none = 'None'
    m4_super90 = 'M4 Super90'
    nova_pump = 'Nova Pump'
    shotgun = 'Shotgun'
    less_lethal_shotgun = 'Less Lethal Shotgun'
    pepper_ball = 'Pepper-ball'
    colt_m4a1_carbine = 'Colt M4A1 Carbine'
    ak_47_machinegun = 'AK-47 Machinegun'
    gb36s_assault_rifle = 'GB36s Assault Rifle'
    gal_sub_machinegun = 'Gal Sub-machinegun'
    _9mm_smg = '9mm SMG'
    suppressed_9mm_smg = 'Suppressed 9mm SMG'
    _45_smg = '.45 SMG'
    m1911_handgun = 'M1911 Handgun'
    _9mm_handgun = '9mm Handgun'
    colt_python = 'Colt Python'
    taser_stun_gun = 'Taser Stun Gun'
    vip_colt_m1911_handgun = 'VIP Colt M1911 Handgun'
    cs_gas_vip = 'CS Gas VIP'
    light_armor = 'Light Armor'
    heavy_armor = 'Heavy Armor'
    gas_mask = 'Gas Mask'
    helmet = 'Helmet'
    flashbang = 'Flashbang'
    cs_gas = 'CS Gas'
    stinger = 'Stinger'
    pepper_spray = 'Pepper Spray'
    optiwand = 'Optiwand'
    toolkit = 'Toolkit'
    door_wedge = 'Door Wedge'
    c2_x3 = 'C2 (x3)'
    the_detonator = 'The Detonator'
    zip_cuffs = 'Zip-cuffs'
    iamcuffed = 'IAmCuffed'
    colt_accurized_rifle = 'Colt Accurized Rifle'
    _40mm_grenade_launcher = '40mm Grenade Launcher'
    _5_56mm_light_machine_gun = '5.56mm Light Machine Gun'
    _5_7x28mm_submachine_gun = '5.7x28mm Submachine Gun'
    mark_19_semi_automatic_pistol = 'Mark 19 Semi-Automatic Pistol'
    _9mm_machine_pistol = '9mm Machine Pistol'
    cobra_stun_gun = 'Cobra Stun Gun'
    ammo_pouch = 'Ammo Pouch'
    no_armor = 'No Armor'
    night_vision_goggles = 'Night Vision Goggles'
    stinger_grenade = 'Stinger Grenade'
    cs_gas_grenade = 'CS Gas Grenade'
    flashbang_grenade = 'Flashbang Grenade'
    baton_grenade = 'Baton Grenade'

    @classmethod
    def primary_weapons(cls) -> tuple['Equipment', ...]:
        return (
            cls.m4_super90,
            cls.nova_pump,
            cls.pepper_ball,
            cls.less_lethal_shotgun,
            cls.colt_m4a1_carbine,
            cls.ak_47_machinegun,
            cls.gb36s_assault_rifle,
            cls.gal_sub_machinegun,
            cls._9mm_smg,
            cls.suppressed_9mm_smg,
            cls._45_smg,
            cls.colt_accurized_rifle,
            cls._40mm_grenade_launcher,
            cls._5_56mm_light_machine_gun,
            cls._5_7x28mm_submachine_gun,
            cls._9mm_machine_pistol,
        )

    @classmethod
    def secondary_weapons(cls) -> tuple['Equipment', ...]:
        return (
            cls.taser_stun_gun,
            cls.cobra_stun_gun,
            cls.m1911_handgun,
            cls._9mm_handgun,
            cls.colt_python,
            cls.vip_colt_m1911_handgun,
            cls.mark_19_semi_automatic_pistol,
        )

    @classmethod
    def grenades(cls) -> tuple['Equipment', ...]:
        return cls.stinger, cls.cs_gas, cls.flashbang


class Ammo(StrEnum):
    none = 'None'
    m4_super90_sg_ammo = 'M4Super90SGAmmo'
    m4_super90_sg_sabot_ammo = 'M4Super90SGSabotAmmo'
    nova_pump_sg_ammo = 'NovaPumpSGAmmo'
    nova_pump_sg_sabot_ammo = 'NovaPumpSGSabotAmmo'
    less_lethal_ammo = 'LessLethalAmmo'
    cs_ball_launcher_ammo = 'CSBallLauncherAmmo'
    m4a1mg_jhp = 'M4A1MG_JHP'
    m4a1mg_fmj = 'M4A1MG_FMJ'
    ak47mg_fmj = 'AK47MG_FMJ'
    ak47mg_jhp = 'AK47MG_JHP'
    g36kmg_fmj = 'G36kMG_FMJ'
    g36kmg_jhp = 'G36kMG_JHP'
    uzismg_fmj = 'UZISMG_FMJ'
    uzismg_jhp = 'UZISMG_JHP'
    mp5smg_jhp = 'MP5SMG_JHP'
    mp5smg_fmj = 'MP5SMG_FMJ'
    ump45_smg_fmj = 'UMP45SMG_FMJ'
    ump45_smg_jhp = 'UMP45SMG_JHP'
    colt_m1911_hg_jhp = 'ColtM1911HG_JHP'
    colt_m1911_hg_fmj = 'ColtM1911HG_FMJ'
    glock_9mm_hg_jhp = 'Glock9mmHG_JHP'
    glock_9mm_hg_fmj = 'Glock9mmHG_FMJ'
    python_revolver_hg_fmj = 'PythonRevolverHG_FMJ'
    python_revolver_hg_jhp = 'PythonRevolverHG_JHP'
    taser_ammo = 'TaserAmmo'
    vip_pistol_ammo_fmj = 'VIPPistolAmmo_FMJ'
    colt_ar_fmj = 'ColtAR_FMJ'
    hk69gl_stinger_grenade_ammo = 'HK69GL_StingerGrenadeAmmo'
    hk69gl_flashbang_grenade_ammo = 'HK69GL_FlashbangGrenadeAmmo'
    hk69gl_csgas_grenade_ammo = 'HK69GL_CSGasGrenadeAmmo'
    hk69gl_triple_baton_ammo = 'HK69GL_TripleBatonAmmo'
    sawmg_jhp = 'SAWMG_JHP'
    sawmg_fmj = 'SAWMG_FMJ'
    fnp90_smg_fmj = 'FNP90SMG_FMJ'
    fnp90_smg_jhp = 'FNP90SMG_JHP'
    dehg_fmj = 'DEHG_FMJ'
    dehg_jhp = 'DEHG_JHP'
    tec9_smg_fmj = 'TEC9SMG_FMJ'
