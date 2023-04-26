import logging
from collections import defaultdict
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models import Sum, Max, Count, Case, When, Q, Min, Value
from django.db.models.functions import NullIf, Cast, Round

from apps.tracker.entities import Team, GameType, GameOutcome, Equipment

if TYPE_CHECKING:
    from apps.tracker.models import Profile, Server  # noqa

logger = logging.getLogger(__name__)

q_qualified_weapons = Q(weapon__name__in=[
    Equipment.m4_super90,
    Equipment.nova_pump,
    Equipment.shotgun,
    Equipment.colt_m4a1_carbine,
    Equipment.ak_47_machinegun,
    Equipment.gb36s_assault_rifle,
    Equipment.gal_sub_machinegun,
    Equipment._9mm_smg,
    Equipment.suppressed_9mm_smg,
    Equipment._45_smg,
    Equipment.m1911_handgun,
    Equipment._9mm_handgun,
    Equipment.colt_python,
    Equipment.vip_colt_m1911_handgun,
    Equipment.colt_accurized_rifle,
    Equipment._5_56mm_light_machine_gun,
    Equipment._5_7x28mm_submachine_gun,
    Equipment.mark_19_semi_automatic_pistol,
    Equipment._9mm_machine_pistol,
])
q_qualified_grenades = Q(weapon__name__in=Equipment.grenades())

q_versus_modes = Q(game__gametype__in=GameType.versus_modes())
q_coop_modes = Q(game__gametype=GameType.co_op)

q_vip_victories = Q(vip=True, game__outcome__in=GameOutcome.swat_victories())
q_draw_games = Q(game__outcome=GameOutcome.tie)
q_swat_victories = Q(team=Team.swat, game__outcome__in=GameOutcome.swat_victories())
q_swat_losses = Q(team=Team.swat, game__outcome__in=GameOutcome.sus_victories())
q_sus_victories = Q(team=Team.suspects, game__outcome__in=GameOutcome.sus_victories())
q_sus_losses = Q(team=Team.suspects, game__outcome__in=GameOutcome.swat_victories())
q_coop_victories = Q(game__outcome=GameOutcome.coop_completed)
q_coop_losses = Q(game__outcome=GameOutcome.coop_failed)


class PlayerQuerySet(models.QuerySet):
    as_float = partial(Cast, output_field=models.FloatField())

    _agg_player_score = Sum(Case(When(q_versus_modes, then='score')))
    _agg_player_time = Sum(Case(When(q_versus_modes, then='time')))
    _agg_player_games = Count(Case(When(q_versus_modes, then='game')), distinct=True)
    _agg_player_kills = Sum(Case(When(q_versus_modes, then='kills')))
    _agg_player_deaths = Sum(Case(When(q_versus_modes, then='deaths')))
    _agg_player_weapon_shots = Sum(Case(When(q_qualified_weapons, then='weapon__shots')))
    _agg_player_weapon_hits = Sum(Case(When(q_qualified_weapons, then='weapon__hits')))
    _agg_player_weapon_kills = Sum(Case(When(q_qualified_weapons, then='weapon__kills')))
    _agg_player_weapon_teamhits = Sum(Case(When(q_qualified_weapons, then='weapon__teamhits')))
    _agg_player_grenade_shots = Sum(Case(When(q_qualified_grenades, then='weapon__shots')))
    _agg_player_grenade_hits = Sum(Case(When(q_qualified_grenades, then='weapon__hits')))
    _agg_player_grenade_kills = Sum(Case(When(q_qualified_grenades, then='weapon__kills')))
    _agg_player_grenade_teamhits = Sum(Case(When(q_qualified_grenades, then='weapon__teamhits')))

    # main player stats - no grouping
    player_aggregates = [{
        'score': _agg_player_score,
        'top_score': Max(Case(When(q_versus_modes, then='score'))),
        'time': _agg_player_time,
        'games': _agg_player_games,
        'wins': Count(Case(When(q_swat_victories | q_sus_victories, then='game')), distinct=True),
        'losses': Count(Case(When(q_swat_losses | q_sus_losses, then='game')), distinct=True),
        'draws': Count(Case(When(q_draw_games, then='game')), distinct=True),
        'spm_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_time, Value(0)) * Value(60), 4),
        'spr_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_games, Value(0)), 4),
        'kills': _agg_player_kills,
        'teamkills': Sum(Case(When(q_versus_modes, then='teamkills'))),
        'top_kills': Max(Case(When(q_versus_modes, then='kills'))),
        'arrests': Sum(Case(When(q_versus_modes, then='arrests'))),
        'top_arrests': Max(Case(When(q_versus_modes, then='arrests'))),
        'arrested': Sum(Case(When(q_versus_modes, then='arrested'))),
        'deaths': _agg_player_deaths,
        'top_kill_streak': Max(Case(When(q_versus_modes, then='kill_streak'))),
        'top_arrest_streak': Max(Case(When(q_versus_modes, then='arrest_streak'))),
        'top_death_streak': Max(Case(When(q_versus_modes, then='death_streak'))),
        'kd_ratio': Round(as_float(_agg_player_kills) / NullIf(_agg_player_deaths, Value(0)), 4),
    }, {
        'weapon_shots': _agg_player_weapon_shots,
        'weapon_hits': _agg_player_weapon_hits,
        'weapon_kills': _agg_player_weapon_kills,
        'weapon_teamhits': _agg_player_weapon_teamhits,
        'weapon_hit_ratio': Round(as_float(_agg_player_weapon_hits)
                                  / NullIf(_agg_player_weapon_shots, Value(0)), 4),
        'weapon_kill_ratio': Round(as_float(_agg_player_weapon_kills)
                                   / NullIf(_agg_player_weapon_shots, Value(0)), 4),
        'weapon_teamhit_ratio': Round(as_float(_agg_player_weapon_teamhits)
                                      / NullIf(_agg_player_weapon_shots, Value(0)), 4),
        'grenade_shots': _agg_player_grenade_shots,
        'grenade_hits': _agg_player_grenade_hits,
        'grenade_kills': _agg_player_grenade_kills,
        'grenade_teamhits': _agg_player_grenade_teamhits,
        'grenade_hit_ratio': Round(as_float(_agg_player_grenade_hits)
                                   / NullIf(_agg_player_grenade_shots, Value(0)), 4),
        'grenade_teamhit_ratio': Round(as_float(_agg_player_grenade_teamhits)
                                       / NullIf(_agg_player_grenade_shots, Value(0)), 4),
    }]

    # player stats per gametype
    gametype_aggregates = [{
        'score': _agg_player_score,
        'top_score': Max(Case(When(q_versus_modes, then='score'))),
        'time': _agg_player_time,
        'games': _agg_player_games,
        'wins': Count(Case(When(q_swat_victories | q_sus_victories, then='game')), distinct=True),
        'losses': Count(Case(When(q_swat_losses | q_sus_losses, then='game')), distinct=True),
        'draws': Count(Case(When(q_draw_games, then='game')), distinct=True),
        'kills': _agg_player_kills,
        'arrests': Sum(Case(When(q_versus_modes, then='arrests'))),
        'top_kill_streak': Max(Case(When(q_versus_modes, then='kill_streak'))),
        'top_arrest_streak': Max(Case(When(q_versus_modes, then='arrest_streak'))),
        'spm_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_time, Value(0)) * Value(60), 4),
        'spr_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_games, Value(0)), 4),
        # vip related stats
        'vip_escapes': Sum('vip_escapes'),
        'vip_captures': Sum('vip_captures'),
        'vip_rescues': Sum('vip_rescues'),
        'vip_kills_valid': Sum('vip_kills_valid'),
        'vip_kills_invalid': Sum('vip_kills_invalid'),
        'vip_times': Count(Case(When(vip=True, then='pk')), distinct=True),
        'vip_wins': Count(Case(When(q_vip_victories, then='pk')), distinct=True),
        # rd stats
        'rd_bombs_defused': Sum('rd_bombs_defused'),
        # sg stats
        'sg_escapes': Sum('sg_escapes'),
        'sg_kills': Sum('sg_kills'),
        # COOP stats
        'coop_score': Sum('game__coop_score'),
        'coop_top_score': Max('game__coop_score'),
        'coop_time': Sum(Case(When(q_coop_modes, then='game__time'))),
        'coop_games': Count(Case(When(q_coop_modes, then='game')), distinct=True),
        'coop_wins': Count(Case(When(q_coop_victories, then='game')), distinct=True),
        'coop_losses': Count(Case(When(q_coop_losses, then='game')), distinct=True),
        'coop_hostage_arrests': Sum('coop_hostage_arrests'),
        'coop_hostage_hits': Sum('coop_hostage_hits'),
        'coop_hostage_incaps': Sum('coop_hostage_incaps'),
        'coop_hostage_kills': Sum('coop_hostage_kills'),
        'coop_enemy_arrests': Sum('coop_enemy_arrests'),
        'coop_enemy_incaps': Sum('coop_enemy_incaps'),
        'coop_enemy_kills': Sum('coop_enemy_kills'),
        'coop_enemy_incaps_invalid': Sum('coop_enemy_incaps_invalid'),
        'coop_enemy_kills_invalid': Sum('coop_enemy_kills_invalid'),
        'coop_toc_reports': Sum('coop_toc_reports'),
    }]

    _agg_weapon_shots = Sum('weapon__shots')
    _agg_weapon_hits = Sum('weapon__hits')
    _agg_weapon_teamhits = Sum('weapon__teamhits')
    _agg_weapon_kills = Sum('weapon__kills')
    # player stats per weapon
    weapon_aggregates = [{
        'shots': _agg_weapon_shots,
        'time': Sum('weapon__time'),
        'hits': _agg_weapon_hits,
        'teamhits': _agg_weapon_teamhits,
        'kills': _agg_weapon_kills,
        'teamkills': Sum('weapon__teamkills'),
        'hit_ratio': Round(as_float(_agg_weapon_hits) / NullIf(_agg_weapon_shots, Value(0)), 4),
        'kill_ratio': Round(as_float(_agg_weapon_kills) / NullIf(_agg_weapon_shots, Value(0)), 4),
        'teamhit_ratio': Round(as_float(_agg_weapon_teamhits) / NullIf(_agg_weapon_shots, Value(0)), 4)
    }]

    server_aggregates = [{
        'score': _agg_player_score,
        'time': _agg_player_time,
        'games': _agg_player_games,
        'kills': _agg_player_kills,
        'deaths': _agg_player_deaths,
        'arrests': Sum(Case(When(q_versus_modes, then='arrests'))),
        'spm_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_time, Value(0)) * Value(60), 4),
        'spr_ratio': Round(as_float(_agg_player_score) / NullIf(_agg_player_games, Value(0)), 4),
        'top_kill_streak': Max(Case(When(q_versus_modes, then='kill_streak'))),
        'top_arrest_streak': Max(Case(When(q_versus_modes, then='arrest_streak'))),
        'kd_ratio': Round(as_float(_agg_player_kills) / NullIf(_agg_player_deaths, Value(0)), 4),
        'coop_score': Sum(Case(When(q_coop_modes, then='game__coop_score'))),
        'coop_games': Count(Case(When(q_coop_modes, then='game')), distinct=True),
        'coop_time': Sum(Case(When(q_coop_modes, then='game__time'))),
    }]

    map_aggregates = server_aggregates + [{
        'top_score': Max(Case(When(q_versus_modes, then='score'))),
        'wins': Count(Case(When(q_swat_victories | q_sus_victories, then='game')), distinct=True),
        'losses': Count(Case(When(q_swat_losses | q_sus_losses, then='game')), distinct=True),
        'draws': Count(Case(When(q_draw_games, then='game')), distinct=True),
        'coop_top_score': Max(Case(When(q_coop_modes, then='game__coop_score'))),
        'coop_wins': Count(Case(When(q_coop_victories, then='game')), distinct=True),
        'coop_losses': Count(Case(When(q_coop_losses, then='game')), distinct=True),
        'coop_best_time': Min(Case(When(q_coop_victories, then='game__time'))),
        'coop_worst_time': Max(Case(When(q_coop_victories, then='game__time'))),
        'vip_escape_time': Min(Case(When(Q(vip=True, vip_escapes=1, game__player_num__gte=14), then='time'))),
    }]

    def with_qualified_games(self) -> 'PlayerQuerySet':
        """
        Include game rounds that have enough players to be qualified (except for CO-OP games)
        """
        return self.filter(Q(game__player_num__gte=settings.TRACKER_MIN_PLAYERS) |
                           Q(q_coop_modes))

    def for_period(self, start_date: datetime, end_date: datetime) -> 'PlayerQuerySet':
        """
        Filter games by period tuple.
        """
        return self.filter(Q(game__date_finished__gte=start_date,
                             game__date_finished__lte=end_date))

    def for_server(self, server: 'Server') -> 'PlayerQuerySet':
        return self.filter(game__server=server)

    def for_profile(self, profile: 'Profile') -> 'PlayerQuerySet':
        return self.filter(alias__profile=profile)

    def aggregate_player_stats(self) -> dict[str, int | float]:
        return (self.filter(q_versus_modes)
                    .aggregate_stats_groups(self.player_aggregates))

    def aggregate_stats_by_weapon(self) -> dict[str, dict[str, int | float]]:
        return (self.filter(q_versus_modes)
                    .aggregate_stats_groups_by(self.weapon_aggregates, group_by='weapon__name'))

    def aggregate_stats_by_map(self) -> dict[str, dict[str, int | float]]:
        return self.aggregate_stats_groups_by(self.map_aggregates, group_by='game__map_id')

    def aggregate_stats_by_server(self) -> dict[str, dict[str, int | float]]:
        return self.aggregate_stats_groups_by(self.server_aggregates, group_by='game__server_id')

    def aggregate_stats_by_gametype(self) -> dict[str, dict[str, int | float]]:
        return self.aggregate_stats_groups_by(self.gametype_aggregates, group_by='game__gametype')

    def aggregate_stats_groups(self, aggregate_groups: list[dict[str, models.Aggregate]]) -> dict[str, int | float]:
        result = {}
        for group in aggregate_groups:
            prepared_aggregates = self._prepare_aggregates(group)
            group_stats = self.aggregate(**prepared_aggregates)
            group_stats = self._finalize_aggregates(group_stats)
            result.update(group_stats)
        return result

    def aggregate_stats_groups_by(
        self,
        aggregate_groups: list[dict[str, models.Aggregate]],
        *,
        group_by: str,
    ) -> dict[str, dict[str, int | float]]:
        result = defaultdict(dict)
        for group in aggregate_groups:
            grouped_stats = self.aggregate_stats_by(group, group_by=group_by)
            for grouping_key, stats in grouped_stats.items():
                result[grouping_key].update(stats)
        return result

    def aggregate_stats_by(self,
                           aggregates: dict[str, models.Aggregate],
                           *,
                           group_by: str) -> dict[str, dict[str, int | float]]:
        result = {}

        prepared_aggregates = self._prepare_aggregates(aggregates)
        grouped_items = (self
                         .order_by(group_by)
                         .values(group_by)
                         .annotate(**prepared_aggregates))
        # turn a list of grouped items
        # into a dictionary mapping grouping keys to the items
        for grouped_item in grouped_items:
            grouped_item = self._finalize_aggregates(grouped_item)
            grouping_key = grouped_item.pop(group_by)
            result[grouping_key] = grouped_item

        return result

    def _prepare_aggregates(self, aggregates: dict[str, models.Aggregate]) -> dict[str, models.Aggregate]:
        prepared_aggregates = {}
        for key in list(aggregates):
            prepared_aggregates[f'_{key}'] = aggregates[key]
        return prepared_aggregates

    def _finalize_aggregates(self, aggregated_items: dict[str, int | float | str]) -> dict[str, int | float | str]:
        items = {}
        # strip prefixed keys
        for key, value in aggregated_items.items():
            if key.startswith('_'):
                key = key[1:]
            items[key] = value
        return items


class PlayerManager(models.Manager):

    def get_queryset(self):
        return (super().get_queryset()
                .select_related('loadout', 'alias', 'alias__isp', 'alias__profile'))
