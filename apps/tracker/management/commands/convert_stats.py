import logging

from django.core.management.base import BaseCommand

from apps.tracker.models import PlayerStats

logger = logging.getLogger(__name__)

category_mapping = {
    0: 'score',
    1: 'time',
    2: 'games',
    3: 'wins',
    4: 'losses',
    5: 'draws',
    6: 'kills',
    7: 'arrests',
    8: 'deaths',
    9: 'arrested',
    10: 'teamkills',
    11: 'top_score',
    12: 'top_kill_streak',
    13: 'top_arrest_streak',
    14: 'top_death_streak',
    15: 'vip_escapes',
    16: 'vip_captures',
    17: 'vip_rescues',
    18: 'vip_kills_valid',
    19: 'vip_kills_invalid',
    20: 'vip_times',
    21: 'rd_bombs_defused',
    22: 'sg_escapes',
    23: 'sg_kills',
    24: 'spm_ratio',
    25: 'spr_ratio',
    26: 'kd_ratio',
    27: 'coop_games',
    28: 'coop_time',
    29: 'coop_wins',
    30: 'coop_losses',
    31: 'coop_hostage_arrests',
    32: 'coop_hostage_hits',
    33: 'coop_hostage_incaps',
    34: 'coop_hostage_kills',
    35: 'coop_enemy_arrests',
    37: 'coop_enemy_incaps',
    38: 'coop_enemy_kills',
    39: 'coop_enemy_incaps_invalid',
    40: 'coop_enemy_kills_invalid',
    41: 'coop_toc_reports',
    42: 'coop_score',
    45: 'suicides',
    46: 'top_kills',
    47: 'top_arrests',
    48: 'weapon_shots',
    49: 'weapon_hits',
    50: 'weapon_hit_ratio',
    51: 'weapon_distance',
    60: 'average_arrest_streak',
    61: 'average_death_streak',
    62: 'average_kill_streak',
    63: 'coop_best_time',
    64: 'coop_top_score',
    65: 'coop_worst_time',
    66: 'distance',
    67: 'grenade_hit_ratio',
    68: 'grenade_hits',
    69: 'grenade_kills',
    70: 'grenade_shots',
    71: 'grenade_teamhit_ratio',
    72: 'grenade_teamhits',
    73: 'hit_ratio',
    74: 'hits',
    75: 'kill_ratio',
    76: 'shots',
    77: 'teamhit_ratio',
    78: 'teamhits',
    79: 'vip_escape_time',
    80: 'vip_wins',
    81: 'weapon_kill_ratio',
    82: 'weapon_kills',
    83: 'weapon_teamhit_ratio',
    84: 'weapon_teamhits'
}


def convert_rank_categories():
    for category_legacy, category_enum in category_mapping.items():
        queryset = (PlayerStats.objects
                    .filter(category_legacy=category_legacy, category__isnull=True))
        updated_num = queryset.update(category=category_enum)
        logger.info('converted %s rows from %s to %s', updated_num, category_legacy, category_enum)


class Command(BaseCommand):

    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)
        convert_rank_categories()
