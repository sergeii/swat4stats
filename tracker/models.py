import re
import datetime
import logging

import pytz
from django.conf import settings
from django.db import models, transaction
from django.db.models import Q, When, Case, Count, Sum, Max, Func, F
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Upper
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe, escape

import markdown
import bleach

from vendor import julia

from .utils import lock, force_ipy, calc_ratio
from . import definitions, const, utils
from .definitions import STAT

logger = logging.getLogger(__name__)


class GameMixin:

    @property
    def gametype_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'gametype', str(self.gametype)
        )

    @property
    def mapname_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'mapname', str(self.mapname)
        )


class ServerManager(models.Manager):

    def enabled(self):
        return self.get_queryset().filter(enabled=True)

    def streamed(self):
        return self.enabled().filter(streamed=True)


class Server(models.Model):
    ip = models.GenericIPAddressField(protocol='IPv4')
    port = models.PositiveIntegerField()

    enabled = models.BooleanField(default=False)
    streamed = models.BooleanField(default=False)
    listed = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    # query ports
    port_gs1 = models.PositiveIntegerField(null=True, blank=True)
    port_gs2 = models.PositiveIntegerField(null=True, blank=True)
    # ip-based country code
    country = models.CharField(max_length=2, null=True, blank=True)
    # cached hostname
    hostname = models.CharField(max_length=256, null=True, blank=True)
    # stats mod version
    version = models.CharField(max_length=64, null=True, blank=True)

    objects = ServerManager()

    class Meta:
        unique_together = (('ip', 'port'),)
        indexes = [
            models.Index(Func(F('ip'), function='host'), F('port'), name='tracker_server_host_ip_port'),
        ]

    @property
    def name(self):
        if self.hostname:
            return utils.force_clean_name(self.hostname)
        return f'{self.ip}:{self.port}'

    def __str__(self):
        return self.name


class Game(models.Model, GameMixin):
    server = models.ForeignKey('Server', on_delete=models.PROTECT)
    tag = models.CharField(max_length=8, null=True, unique=True)
    time = models.SmallIntegerField(default=0)
    outcome = models.SmallIntegerField(default=0)
    gametype = models.SmallIntegerField(null=True)
    mapname = models.SmallIntegerField(null=True)
    player_num = models.SmallIntegerField(default=0)
    score_swat = models.SmallIntegerField(default=0)
    score_sus = models.SmallIntegerField(default=0)
    vict_swat = models.SmallIntegerField(default=0)
    vict_sus = models.SmallIntegerField(default=0)
    rd_bombs_defused = models.SmallIntegerField(default=0)
    rd_bombs_total = models.SmallIntegerField(default=0)
    coop_score = models.SmallIntegerField(default=0)
    date_finished = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index((F('score_swat') + F('score_sus')).desc(), name='tracker_game_score_swat_score_sus'),
            models.Index(F('date_finished').desc(), name='tracker_game_date_finished_desc'),
        ]

    @property
    def outcome_translated(self):
        """
        Translate the outcome integer code to a human-readable name.
        """
        return julia.shortcuts.map(definitions.stream_pattern_node, 'outcome', str(self.outcome))

    @property
    def date_started(self):
        """
        Calculate and return the date of the game start based on the game duration.
        """
        return self.date_finished - datetime.timedelta(seconds=self.time)

    @property
    def winner(self):
        """
        Return the winner team number.

        0 - SWAT
        1 - Suspects
        2 - Tie
        """
        assert isinstance(self.outcome, int)
        if self.outcome in definitions.SWAT_GAMES:
            return 0
        elif self.outcome in definitions.SUS_GAMES:
            return 1
        elif self.outcome in definitions.DRAW_GAMES:
            return 2
        return None

    @property
    def coop_game(self):
        """
        Tell whether this was a COOP game.
        """
        assert isinstance(self.gametype, int)
        if self.gametype in definitions.MODES_COOP:
            return True
        return False

    @property
    def coop_successful(self):
        """
        Tell whether the COOP game was successful.
        """
        assert isinstance(self.outcome, int)
        if self.outcome in definitions.COMPLETED_MISSIONS:
            return True
        elif self.outcome in definitions.FAILED_MISSIONS:
            return False
        return None

    @property
    def coop_score_normal(self):
        """
        Normalize the COOP (>=0, <=100) score and return the result.
        """
        return max(0, min(100, self.coop_score))

    @property
    def best_player(self):
        """Return the player of the game."""
        # best to be used with prefetch_related
        players = list(self.player_set.all())
        # separate players
        swat = [player for player in players if player.team == definitions.TEAM_BLUE]
        suspects = [player for player in players if player.team == definitions.TEAM_RED]
        # use the following attrs as a fallback
        comparable = ['score', 'kills', 'arrests', '-deaths', '-arrested']
        sortable = players
        # there is no best player in COOP ;-)
        if self.gametype in definitions.MODES_COOP:
            return None
        if self.gametype == definitions.MODE_VIP:
            # get the best SWAT player in the VIP escort game
            if self.outcome in definitions.SWAT_GAMES:
                sortable = swat
                comparable = ['-vip_kills_invalid', 'vip_rescues', 'vip_escapes'] + comparable
            # get the best suspects player in the VIP escort game
            elif self.outcome in definitions.SUS_GAMES:
                sortable = suspects
                comparable = ['-vip_kills_invalid', 'vip_captures', 'vip_kills_valid'] + comparable
        else:
            pass
        sortable = sorted(sortable, key=utils.sort_key(*comparable), reverse=True)
        return next(iter(sortable), None)

    def __str__(self):
        return f'{self.date_finished} - {self.time} - {self.outcome}'


class Loadout(models.Model):
    FIELDS = (
        'primary',
        'secondary',
        'primary_ammo',
        'secondary_ammo',
        'head',
        'body',
        'equip_one',
        'equip_two',
        'equip_three',
        'equip_four',
        'equip_five',
        'breacher',
    )

    primary = models.SmallIntegerField(default=0)
    primary_ammo = models.SmallIntegerField(default=0)
    secondary = models.SmallIntegerField(default=0)
    secondary_ammo = models.SmallIntegerField(default=0)
    equip_one = models.SmallIntegerField(default=0)
    equip_two = models.SmallIntegerField(default=0)
    equip_three = models.SmallIntegerField(default=0)
    equip_four = models.SmallIntegerField(default=0)
    equip_five = models.SmallIntegerField(default=0)
    breacher = models.SmallIntegerField(default=0)
    head = models.SmallIntegerField(default=0)
    body = models.SmallIntegerField(default=0)

    def __str__(self):
        # Pepper-ball:Taser Stun Gun, etc
        return ':'.join([
            const.EQUIPMENT[str(getattr(self, key))] for key in self.FIELDS
        ])


class Weapon(models.Model):
    id = models.BigAutoField(primary_key=True)
    player = models.ForeignKey('Player', on_delete=models.CASCADE)
    name = models.SmallIntegerField()
    time = models.SmallIntegerField(default=0)
    shots = models.SmallIntegerField(default=0)
    hits = models.SmallIntegerField(default=0)
    teamhits = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    teamkills = models.SmallIntegerField(default=0)
    distance = models.FloatField(default=0)  # in meters

    def __str__(self):
        return const.EQUIPMENT[str(self.name)]


class AliasManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related()


class Alias(models.Model):
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    isp = models.ForeignKey('ISP', related_name='+', null=True, on_delete=models.PROTECT)

    objects = AliasManager()

    class Meta:
        index_together = (('name', 'isp'),)
        indexes = [
            models.Index(Upper('name'), F('isp_id'), name='tracker_alias_upper_name_isp_id')
        ]

    def __str__(self):
        return f'{self.name}, {self.isp}'


class PlayerManager(models.Manager):

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('loadout', 'alias', 'alias__isp', 'alias__profile')
        )

    def prefetched(self):
        return self.get_queryset().prefetch_related('weapon_set')

    def qualified(self, start, end, filters=None):
        """
        Return a player_set queryset filtered by year and number of players
        that have participated in the related games.

        Args:
            start, end - start and end dates
            filters - optional lookup attr dict
        """
        args = [
            # limit the queryset to the specified period
            models.Q(game__date_finished__gte=start,
                     game__date_finished__lte=end),
            # limit the queryset with the min number of players played in a game
            (models.Q(game__player_num__gte=Profile.MIN_PLAYERS)
             # unless it's a COOP game
             | models.Q(game__gametype__in=definitions.MODES_COOP)),
        ]
        # append extra filters
        if filters:
            args.append(models.Q(**filters))
        return self.filter(*args)


class Player(models.Model):
    MIN_AMMO = 30  # min ammo required for accuracy calculation

    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    alias = models.ForeignKey('Alias', on_delete=models.PROTECT)
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.PROTECT)
    ip = models.GenericIPAddressField(protocol='IPv4')

    team = models.SmallIntegerField(null=True)
    vip = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    dropped = models.BooleanField(default=False)
    coop_status = models.SmallIntegerField(default=0)

    score = models.SmallIntegerField(default=0)
    time = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    teamkills = models.SmallIntegerField(default=0)
    deaths = models.SmallIntegerField(default=0)
    suicides = models.SmallIntegerField(default=0)
    arrests = models.SmallIntegerField(default=0)
    arrested = models.SmallIntegerField(default=0)
    kill_streak = models.SmallIntegerField(default=0)
    arrest_streak = models.SmallIntegerField(default=0)
    death_streak = models.SmallIntegerField(default=0)
    vip_captures = models.SmallIntegerField(default=0)
    vip_rescues = models.SmallIntegerField(default=0)
    vip_escapes = models.SmallIntegerField(default=0)
    vip_kills_valid = models.SmallIntegerField(default=0)
    vip_kills_invalid = models.SmallIntegerField(default=0)
    rd_bombs_defused = models.SmallIntegerField(default=0)
    sg_escapes = models.SmallIntegerField(default=0)
    sg_kills = models.SmallIntegerField(default=0)
    coop_hostage_arrests = models.SmallIntegerField(default=0)
    coop_hostage_hits = models.SmallIntegerField(default=0)
    coop_hostage_incaps = models.SmallIntegerField(default=0)
    coop_hostage_kills = models.SmallIntegerField(default=0)
    coop_enemy_arrests = models.SmallIntegerField(default=0)
    coop_enemy_incaps = models.SmallIntegerField(default=0)
    coop_enemy_kills = models.SmallIntegerField(default=0)
    coop_enemy_incaps_invalid = models.SmallIntegerField(default=0)
    coop_enemy_kills_invalid = models.SmallIntegerField(default=0)
    coop_toc_reports = models.SmallIntegerField(default=0)

    objects = PlayerManager()

    class Meta:
        indexes = [
            models.Index(Func(F('ip'), function='host'), F('id').desc(), name='tracker_player_host_ip_id_desc'),
        ]
        index_together = (
            ('alias', 'score'),
            ('alias', 'kills'),
            ('alias', 'arrests'),
            ('alias', 'kill_streak'),
            ('alias', 'arrest_streak'),
        )

    @property
    def profile(self):
        return self.alias.profile

    @property
    def name(self):
        return self.alias.name

    @property
    def country(self):
        try:
            return self.alias.isp.country
        except AttributeError:
            return None

    @property
    def coop_status_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('players').item,
            'coop_status',
            str(self.coop_status)
        )

    @property
    def special(self):
        return (
            self.vip_escapes +
            self.vip_captures +
            self.vip_rescues +
            self.rd_bombs_defused +
            self.sg_escapes
        )

    def sum_weapon(self, property, interested):
        value = 0
        for weapon in self.weapon_set.all():
            if weapon.name in interested:
                value += getattr(weapon, property)
        return value

    @property
    def ammo_shots(self):
        return self.sum_weapon('shots', definitions.WEAPONS_PRIMARY + definitions.WEAPONS_SECONDARY)

    @property
    def ammo_accuracy(self):
        return utils.calc_accuracy(self.weapon_set.all(), definitions.WEAPONS_FIRED, self.MIN_AMMO)

    def __str__(self):
        return f'{self.name}, {self.ip}'


class Objective(models.Model):
    id = models.BigAutoField(primary_key=True)
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    name = models.SmallIntegerField()
    status = models.SmallIntegerField(default=0)

    @property
    def name_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('coop_objectives').item,
            'name',
            str(self.name)
        )

    @property
    def status_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('coop_objectives').item,
            'status',
            str(self.status)
        )

    def __str__(self):
        return f'{self.name}, {self.status}'


class Procedure(models.Model):
    id = models.BigAutoField(primary_key=True)
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    name = models.SmallIntegerField()
    status = models.CharField(max_length=7)  # xxx/yyy
    score = models.SmallIntegerField(default=0)

    @property
    def name_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('coop_procedures').item,
            'name',
            str(self.name)
        )

    def __str__(self):
        return f'{self.name}, {self.score} ({self.status})'


class IPManager(models.Manager):

    def get_queryset(self):
        """
        Return a queryset with an extra `length` field that
        is equal to the number of ip addresses in the ip range.
        """
        return (
            super().get_queryset()
            .extra(select={'length': '(range_to - range_from)'})
        )


class IP(models.Model):
    isp = models.ForeignKey('ISP', on_delete=models.SET_NULL, null=True)
    range_from = models.BigIntegerField()
    range_to = models.BigIntegerField()
    date_created = models.DateTimeField(auto_now_add=True)

    objects = IPManager()

    class Meta:
        unique_together = (('range_from', 'range_to'),)
        indexes = [
            models.Index(F('range_to') - F('range_from'), name='tracker_ip_length'),
        ]

    def range_from_normal(self):
        """Return the range start address in dotted form."""
        return force_ipy(self.range_from).strNormal(3)
    range_from_normal.admin_order_field = 'range_from'

    def range_to_normal(self):
        """Return the range end address in dotted form."""
        return force_ipy(self.range_to).strNormal(3)
    range_to_normal.admin_order_field = 'range_to'

    def length(self, obj):
        return obj.length
    length.admin_order_field = 'length'

    def __str__(self):
        return f'{self.range_from_normal()}-{self.range_to_normal()}'


class ISP(models.Model):
    name = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=2, null=True)

    def __str__(self):
        return f'{self.name}, {self.country}'


class ProfileManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related('game_last')

    def popular(self):
        """
        Return a queryset with all the (other than loadout and country) popular fields set to a value.
        """
        return (
            self.get_queryset()
            .filter(
                name__isnull=False,
                team__isnull=False,
                game_first__isnull=False,
                game_last__isnull=False
            )
        )


class Profile(models.Model):
    TIME_RECENT = 3600*24*30*6
    TIME_POPULAR = 3600*24*7
    MIN_KILLS = 500     # min kills required for kd ratio calculation
    MIN_TIME = 60*60*10     # min time for score per minute and other time-based ratio
    MIN_GAMES = 250
    MIN_AMMO = 1000     # min ammo required for accuracy calculation
    MIN_PLAYERS = 10    # min players needed for profile stats to be aggregated from the game being quialified
    MIN_NAME_LENGTH = 3     # name with length shorter than this number is considered popular.

    SET_STATS_COMMON = 1
    SET_STATS_KILLS = 2
    SET_STATS_WEAPONS = 4
    SET_STATS_VIP = 8
    SET_STATS_RD = 16
    SET_STATS_SG = 32
    SET_STATS_COOP = 64
    SET_STATS_BS = 128

    SET_STATS_ALL = (
        SET_STATS_COMMON | SET_STATS_KILLS | SET_STATS_WEAPONS |
        SET_STATS_BS | SET_STATS_VIP | SET_STATS_RD | SET_STATS_SG | SET_STATS_COOP
    )

    name = models.CharField(max_length=64, null=True)
    team = models.SmallIntegerField(null=True)
    country = models.CharField(max_length=2, null=True)
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.PROTECT)

    # reference to the first played game
    game_first = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.SET_NULL)
    # reference to the last played game
    game_last = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.SET_NULL)

    objects = ProfileManager()

    def __str__(self):
        return f'{self.name}, {self.country}'

    @property
    def popular(self):
        return self.name and (self.team is not None) and self.game_first and self.game_last

    @property
    def first_seen(self):
        try:
            return self.game_first.date_finished
        except Exception:
            return None

    @property
    def last_seen(self):
        try:
            return self.game_last.date_finished
        except Exception:
            return None

    def fetch_popular_name(self, year=None):
        """Return the profile's most popular name."""
        return self.fetch_popular('alias__name', year)

    def fetch_popular_country(self, year=None):
        """Return the profile's most popular country."""
        return self.fetch_popular('alias__isp__country', year)

    def fetch_popular_team(self, year=None):
        """Return the profile's most popular team."""
        return self.fetch_popular('team', year)

    def fetch_popular_loadout(self, year=None):
        """Return the profile's most popular loadout."""
        # skip the VIP's loadout
        id = self.fetch_popular('loadout', year, Case(When(vip=False, then='loadout')))
        if id:
            return Loadout.objects.get(pk=id)
        return None

    def update_popular(self):
        """
        Fetch the recently popular loadout and update corresponding instance fields.
        """
        for field in ('name', 'team', 'country', 'loadout'):
            # fetch the value
            value = getattr(self, 'fetch_popular_%s' % field)(year=None)
            # only update the instance field if the returned value is not empty
            if value is not None:
                setattr(self, field, value)

    def fetch_popular(self, field, year=None, cond=None):
        """
        Return a profile's most popular item described
        by the `field` name of the related Player entries.

        Item popularity is calculated by aggregating on the number
        of games played in the last Profile.TIME_POPULAR seconds and grouping by `field`.
        The topmost record is assumed to be the most popular item.

        Args:
            field - a GROUP BY field
            year - an optional year (use recent entries if not specified)
            only - an optional conditional Q object
        """
        qs = self.qualified_year(year) if year else self.qualified_recent()
        try:
            annotated = (
                qs
                .values(field)
                .annotate(num=Count(cond if cond else field))
                .order_by('-num')[0:1]
                .get()
            )
        except ObjectDoesNotExist:
            return None
        else:
            return annotated[field]

    def aggregate_mode_stats(self, options, start, end):
        categories = []
        # common stats
        if options & Profile.SET_STATS_COMMON:
            categories.extend([
                STAT.SCORE,
                STAT.TOP_SCORE,
                STAT.TIME,
                STAT.GAMES,
                STAT.WINS,
                STAT.LOSSES,
                STAT.DRAWS,
                # STAT.SPM,  # calculated manually at the bottom of the method
                # STAT.SPR,
            ])
        if options & Profile.SET_STATS_KILLS:
            categories.extend([
                STAT.KILLS,
                STAT.TOP_KILLS,
                STAT.TEAMKILLS,
                STAT.ARRESTS,
                STAT.TOP_ARRESTS,
                STAT.DEATHS,
                STAT.SUICIDES,
                STAT.ARRESTED,
                STAT.KILL_STREAK,
                STAT.ARREST_STREAK,
                STAT.DEATH_STREAK,
                # ammo bases stats
                STAT.AMMO_SHOTS,
                STAT.AMMO_HITS,
                STAT.AMMO_DISTANCE,
                # STAT.AMMO_ACCURACY,  # calculated manually
                # STAT.KDR,
            ])
        # BS stats
        if options & Profile.SET_STATS_BS:
            categories.extend([
                STAT.BS_SCORE,
                STAT.BS_TIME,
            ])
        # VIP Escort stats
        if options & Profile.SET_STATS_VIP:
            categories.extend([
                STAT.VIP_SCORE,
                STAT.VIP_TIME,
                STAT.VIP_ESCAPES,
                STAT.VIP_CAPTURES,
                STAT.VIP_RESCUES,
                STAT.VIP_KILLS_VALID,
                STAT.VIP_KILLS_INVALID,
            ])
        # Rapid Deployment stats
        if options & Profile.SET_STATS_RD:
            categories.extend([
                STAT.RD_SCORE,
                STAT.RD_TIME,
                STAT.RD_BOMBS_DEFUSED,
            ])
        # Smash and Grab stats
        if options & Profile.SET_STATS_SG:
            categories.extend([
                STAT.SG_SCORE,
                STAT.SG_TIME,
                STAT.SG_ESCAPES,
                STAT.SG_KILLS,
            ])
        # COOP stats
        if options & Profile.SET_STATS_COOP:
            categories.extend([
                STAT.COOP_SCORE,
                STAT.COOP_TIME,
                STAT.COOP_GAMES,
                STAT.COOP_WINS,
                STAT.COOP_LOSSES,
                STAT.COOP_TEAMKILLS,
                STAT.COOP_DEATHS,
                STAT.COOP_HOSTAGE_ARRESTS,
                STAT.COOP_HOSTAGE_HITS,
                STAT.COOP_HOSTAGE_INCAPS,
                STAT.COOP_HOSTAGE_KILLS,
                STAT.COOP_ENEMY_ARRESTS,
                STAT.COOP_ENEMY_INCAPS,
                STAT.COOP_ENEMY_KILLS,
                STAT.COOP_ENEMY_INCAPS_INVALID,
                STAT.COOP_ENEMY_KILLS_INVALID,
                STAT.COOP_TOC_REPORTS,
            ])
        aggregated = self.aggregate_player_stats(categories, start, end)
        # Calculate SPM and SPR manually
        if options & Profile.SET_STATS_COMMON:
            # score per minute
            aggregated[STAT.SPM] = calc_ratio(
                aggregated[STAT.SCORE], aggregated[STAT.TIME], min_divisor=Profile.MIN_TIME
            ) * 60
            # score per round
            aggregated[STAT.SPR] = calc_ratio(
                aggregated[STAT.SCORE], aggregated[STAT.GAMES], min_divisor=Profile.MIN_GAMES
            )
        if options & Profile.SET_STATS_KILLS:
            # calculate kills/deaths manually
            aggregated[STAT.KDR] = calc_ratio(
                aggregated[STAT.KILLS], aggregated[STAT.DEATHS], min_divident=self.MIN_KILLS
            )
            # calculate accuracy
            aggregated[STAT.AMMO_ACCURACY] = calc_ratio(
                aggregated[STAT.AMMO_HITS], aggregated[STAT.AMMO_SHOTS], min_divisor=self.MIN_AMMO
            )
        return aggregated

    def aggregate_player_stats(self, stats, start, end):
        aggregates = {
            'game': {
                STAT.SCORE: models.Sum('score'),
                STAT.TOP_SCORE: models.Max('score'),
                # non-COOP time
                STAT.TIME: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='time'))
                    )
                ),
                # non-coop games
                STAT.GAMES: (
                    Count(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='game')),
                        distinct=True
                    )
                ),
                # non-coop wins
                STAT.WINS: (
                    Count(
                        Case(
                            When(
                                Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SWAT_GAMES) |
                                Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SUS_GAMES),
                                then='game'
                            ),
                        ),
                        distinct=True
                    )
                ),
                # non-coop losses
                STAT.LOSSES: (
                    Count(
                        Case(
                            When(
                                Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SUS_GAMES) |
                                Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SWAT_GAMES),
                                then='game'
                            ),
                        ),
                        distinct=True
                    )
                ),
                # non-coop draws
                STAT.DRAWS: (
                    Count(
                        Case(
                            When(
                                Q(game__outcome__in=definitions.DRAW_GAMES,
                                  game__gametype__in=definitions.MODES_VERSUS),
                                then='game'
                            ),
                        ),
                        distinct=True
                    )
                ),
                STAT.KILLS: models.Sum('kills'),
                STAT.TOP_KILLS: models.Max('kills'),
                # non-coop teamkills
                STAT.TEAMKILLS: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='teamkills'))
                    )
                ),
                STAT.ARRESTS: models.Sum('arrests'),
                STAT.TOP_ARRESTS: models.Max('arrests'),
                STAT.ARRESTED: models.Sum('arrested'),
                # non-coop deaths
                STAT.DEATHS: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='deaths'))
                    )
                ),
                # non-coop suicides
                STAT.SUICIDES: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='suicides'))
                    )
                ),
                STAT.KILL_STREAK: models.Max('kill_streak'),
                STAT.ARREST_STREAK: models.Max('arrest_streak'),
                STAT.DEATH_STREAK: (
                    Max(
                        Case(When(game__gametype__in=definitions.MODES_VERSUS, then='death_streak'))
                    )
                ),
                # Barricaded Suspects stats
                STAT.BS_SCORE: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_BS, then='score'))
                    )
                ),
                STAT.BS_TIME: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_BS, then='time'))
                    )
                ),
                # VIP Escort stats
                # Score earned in VIP Escort
                STAT.VIP_SCORE: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_VIP, then='score'))
                    )
                ),
                # Time played in VIP Escort
                STAT.VIP_TIME: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_VIP, then='time'))
                    )
                ),
                STAT.VIP_ESCAPES: Sum('vip_escapes'),
                STAT.VIP_CAPTURES: Sum('vip_captures'),
                STAT.VIP_RESCUES: Sum('vip_rescues'),
                STAT.VIP_KILLS_VALID: Sum('vip_kills_valid'),
                STAT.VIP_KILLS_INVALID: Sum('vip_kills_invalid'),
                STAT.VIP_TIMES: (
                    Count(
                        Case(When(vip=True, then='pk')), distinct=True
                    )
                ),
                # Rapid Deployment stats
                STAT.RD_SCORE: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_RD, then='score'))
                    )
                ),
                STAT.RD_TIME: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_RD, then='time'))
                    )
                ),
                STAT.RD_BOMBS_DEFUSED: models.Sum('rd_bombs_defused'),
                # Smash and Grab stats
                STAT.SG_SCORE: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_SG, then='score'))
                    )
                ),
                STAT.SG_TIME: (
                    Sum(
                        Case(When(game__gametype=definitions.MODE_SG, then='time'))
                    )
                ),
                STAT.SG_ESCAPES: models.Sum('sg_escapes'),
                STAT.SG_KILLS: models.Sum('sg_kills'),
                # COOP stats
                STAT.COOP_SCORE: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_COOP, then='game__coop_score'))
                    )
                ),
                STAT.COOP_TIME: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_COOP, then='time'))
                    )
                ),
                STAT.COOP_GAMES: (
                    Count(
                        Case(When(game__gametype__in=definitions.MODES_COOP, then='game')),
                        distinct=True
                    )
                ),
                STAT.COOP_WINS: (
                    Count(
                        Case(When(game__outcome__in=definitions.COMPLETED_MISSIONS, then='game')),
                        distinct=True
                    )
                ),
                STAT.COOP_LOSSES: (
                    Count(
                        Case(When(game__outcome__in=definitions.FAILED_MISSIONS, then='game')),
                        distinct=True
                    )
                ),
                STAT.COOP_TEAMKILLS: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_COOP, then='teamkills'))
                    )
                ),
                STAT.COOP_DEATHS: (
                    Sum(
                        Case(When(game__gametype__in=definitions.MODES_COOP, then='deaths'))
                    )
                ),
                STAT.COOP_HOSTAGE_ARRESTS: Sum('coop_hostage_arrests'),
                STAT.COOP_HOSTAGE_HITS: Sum('coop_hostage_hits'),
                STAT.COOP_HOSTAGE_INCAPS: Sum('coop_hostage_incaps'),
                STAT.COOP_HOSTAGE_KILLS: Sum('coop_hostage_kills'),
                STAT.COOP_ENEMY_ARRESTS: Sum('coop_enemy_arrests'),
                STAT.COOP_ENEMY_INCAPS: Sum('coop_enemy_incaps'),
                STAT.COOP_ENEMY_KILLS: Sum('coop_enemy_kills'),
                STAT.COOP_ENEMY_INCAPS_INVALID: Sum('coop_enemy_incaps_invalid'),
                STAT.COOP_ENEMY_KILLS_INVALID: Sum('coop_enemy_kills_invalid'),
                STAT.COOP_TOC_REPORTS: Sum('coop_toc_reports'),
            },
            'weapon': {
                # ammo based stats
                STAT.AMMO_SHOTS: (
                    Sum(
                        Case(
                            When(
                                Q(weapon__name__in=definitions.WEAPONS_FIRED,
                                  game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__shots'
                            )
                        )
                    )
                ),
                STAT.AMMO_HITS: (
                    Sum(
                        Case(
                            When(
                                Q(weapon__name__in=definitions.WEAPONS_FIRED,
                                  game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__hits'
                            )
                        )
                    )
                ),
                STAT.AMMO_DISTANCE: (
                    Max(
                        Case(
                            When(
                                Q(weapon__name__in=definitions.WEAPONS_FIRED,
                                  game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__distance'
                            )
                        )
                    )
                ),
            },
        }
        aggregated = {}
        # remove uninteresting aggregates
        for group in list(aggregates.keys()):
            items = aggregates[group]
            for stat in items.copy():
                if stat not in stats:
                    del aggregates[group][stat]
        for items in aggregates.values():
            aggregated.update(self.aggregate(items, start, end))
        # convert null values to zeroes
        return {
            key: value if value else 0
            for key, value in aggregated.items()
        }

    def aggregate_weapon_stats(self, start, end, filters=None):
        """
        Return a dictionary mapping a weapon to a dictionary of the cummulative weapon stats.

        Args:
            start, end - start and end dates

        Example:
            {1: {'shots': 3, 'hits': 1,...}, 2: {'shots': 2, 'hits': 2,...}, ...}
        """
        aggregated = self.aggregate(
            {
                'shots': Sum('weapon__shots'),
                'time': Sum('weapon__time'),
                'hits': Sum('weapon__hits'),
                'teamhits': Sum('weapon__teamhits'),
                'kills': Sum('weapon__kills'),
                'teamkills': Sum('weapon__teamkills'),
                'distance': Max('weapon__distance'),
            },
            start,
            end,
            # group by weapon name
            group_by='weapon__name',
            group_by_as='name',
            filters=filters
        )
        weapons = {}
        for entry in aggregated:
            # calculate accuracy manually (no min_ammo enforcement)
            entry['accuracy'] = calc_ratio(entry['hits'], entry['shots'], min_divisor=self.MIN_AMMO)
            # group by weapon name
            weapons[entry['name']] = entry
        return weapons

    def aggregate(self, items, start, end, group_by=None, group_by_as=None, filters=None):
        """
        Perform an aggregation over fields defined in `items`.
        Aggregation is done in respect to qualified query set.

        Args:
            items - aggregates dictionary
            start, end - start and end dates
            group_by - GROUP BY field
            group_by_as - replace the django generated aggregate field name
            filters - additional filter() kwargs
        """
        keys = {}
        # force dict keys to be strings
        for key in list(items.keys()):
            value = items[key]
            del items[key]
            new_key = str(key)
            items[new_key] = value
            keys[new_key] = key

        qs = self.qualified(start, end, filters=filters)
        # annotate
        if group_by:
            aggregated = qs.order_by(group_by).values(group_by).annotate(**items)
        # aggregate
        else:
            aggregated = qs.aggregate(**items)

        # replace with the original keys
        if not group_by:
            for key in list(aggregated.keys()):
                value = aggregated[key]
                del aggregated[key]
                aggregated[keys[key]] = value
        else:
            # skip None entries that were formed thanks to LEFT OUTER JOIN
            aggregated = list(filter(lambda entry: entry[group_by] is not None, aggregated))
            for entry in aggregated:
                for key, value in entry.items():
                    # replace None values with zeroes
                    entry[key] = value or 0
                # replace the group identifier with a custom one
                # e.g. player__game__mapname -> mapname
                if group_by_as:
                    val = entry[group_by]
                    del entry[group_by]
                    entry[group_by_as] = val
        return aggregated

    def qualified(self, start, end, filters=None):
        filters = filters or {}
        filters.update({
            'alias__profile': self,
        })
        return Player.objects.qualified(start, end, filters)

    def qualified_year(self, year):
        """
        Filter qualified queryset with the specified year.
        """
        return self.qualified(*Rank.get_period_for_year(year))

    def qualified_recent(self):
        """
        Return a player_set queryset filtered with recently played games.
        """
        min_date = timezone.now()-datetime.timedelta(seconds=Profile.TIME_POPULAR)
        return self.qualified(min_date, timezone.now())

    @classmethod
    def is_name_popular(cls, name):
        """
        Tell whether a given name should be considered popular:

            1.  Check length of the name.
                If it's shorter than the predefined value, return True.
            2.  In case the name passes the length validiation,
                attempt to check it against the patterns defined in the const module.
                If the name matches against one of the patterns, return True.
                Return False otherwise.
        Args:
            name - subject string
        """
        if len(name) < cls.MIN_NAME_LENGTH:
            return True
        for pattern in settings.TRACKER_POPULAR_NAMES:
            if re.search(pattern, name, re.I):
                return True
        return False


class RankManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('profile')

    def numbered(self):
        """
        Return a queryset with an extra field describing positions of the selected rows
        in a unique set of category id of ranking period and sorted in ascending order
        by the number of points earned in the specified period.
        """
        return (
            self.get_queryset()
            .extra(
                select={
                    'row_number': ('ROW_NUMBER() OVER(PARTITION BY %s, %s ORDER BY %s DESC, %s ASC)'
                                   % ('category', 'year', 'points', 'id'))
                },
            )
            .order_by('row_number')
        )

    def store(self, category, year, profile, points):
        self.store_many({category: points}, year, profile)

    def store_many(self, items, year, profile):
        # set a list of deleteable categories
        deletable = []
        # assemble a list of categores in question
        categories = list(items.keys())

        with transaction.atomic():
            entries = (
                self.get_queryset()
                .select_for_update()
                .filter(profile=profile, year=year, category__in=categories)
            )
            for entry in entries:
                # zero or negative points - the entry should be deleted
                if items[entry.category] <= 0:
                    deletable.append(entry.pk)
                # points changed - the item should be updated
                elif items[entry.category] != entry.points:
                    entry.points = items[entry.category]
                    entry.save()

                items.pop(entry.category)

            # delete the entries marked for removing
            self.filter(pk__in=deletable).delete()

            creatable = []
            for category, points in items.items():
                if points > 0:
                    creatable.append(self.model(profile=profile, year=year, category=category, points=points))
            # bulk insert the categories that are not present in db
            if creatable:
                self.bulk_create(creatable)

    def rank(self, year):
        sql = f"""
        UPDATE {self.model._meta.db_table} AS t1 SET position = t2.row_number
        FROM
        (
            SELECT ROW_NUMBER() OVER(PARTITION BY category, year ORDER BY points DESC, id ASC), id
            FROM {self.model._meta.db_table}
        ) AS t2
        WHERE t1.id=t2.id AND t1.year = %(year)s
        """
        with transaction.atomic():
            with lock('EXCLUSIVE', self.model) as cursor:
                cursor.execute(sql, {'year': year})


class Rank(models.Model):
    category = models.SmallIntegerField()
    year = models.SmallIntegerField()
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    points = models.FloatField(default=0)
    position = models.PositiveIntegerField(null=True, db_index=True)
    objects = RankManager()

    class Meta:
        unique_together = (('year', 'category', 'profile',),)
        indexes = [
            # FIXME: custom index
            models.Index('year', 'category',
                         condition=Q(position__lte=5),
                         name='tracker_rank_year_category_position_lte')
        ]

    def __str__(self):
        return f'{self.year}:{self.category} #{self.position} {self.profile} ({self.points})'

    @classmethod
    def get_period_for_now(cls):
        """
        Return a 2-tuple of start and end dates for the current year.

        Example:
            (2014-1-1 0:0:0+00, 2014-12-31 23:59:59+00)
        """
        return cls.get_period_for_year(int(timezone.now().strftime('%Y')))

    @classmethod
    def get_period_for_year(cls, year):
        """
        Return a 2-tuple containing start and end dates
        for given year number with respect to given date.

        Args:
            year - year number (eg 2014)
        """
        return (
            datetime.datetime(year, 1, 1, tzinfo=pytz.UTC),
            datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=pytz.UTC)
        )

    @classmethod
    def get_period_for_date(cls, date):
        """
        Return a 2-tuple containing start and end dates for given date.

        Args:
            date - datetime object
        """
        return cls.get_period_for_year(date.year)


class PublishedArticleManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        """
        Return a queryset that would fetch articles with
        the `date_published` column greater or equal to the current time.
        """
        return (
            super().get_queryset(*args, **kwargs)
            .filter(is_published=True, date_published__lte=timezone.now())
        )

    def latest(self, limit):
        """Display the latest `limit` published articles."""
        return self.get_queryset().order_by('-date_published')[:limit]


class Article(models.Model):
    RENDERER_PLAINTEXT = 1
    RENDERER_HTML = 2
    RENDERER_MARKDOWN = 3

    title = models.CharField(blank=True, max_length=64)
    text = models.TextField()
    signature = models.CharField(max_length=128, blank=True)
    is_published = models.BooleanField(default=False)
    date_published = models.DateTimeField(blank=True, default=timezone.now)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    renderer = models.SmallIntegerField(
        choices=(
            (RENDERER_PLAINTEXT, _('Plain text')),
            (RENDERER_HTML, _('HTML')),
            (RENDERER_MARKDOWN, _('Markdown')),
        ),
        default=RENDERER_MARKDOWN
    )

    objects = models.Manager()
    published = PublishedArticleManager()

    # bleach
    ALLOWED_TAGS = [
        'a', 'abbr', 'acronym',
        'b', 'blockquote', 'code', 'em', 'i',
        'li', 'ol', 'strong', 'ul',
        'img', 'iframe',
        'p', 'div',
        'br', 'hr', 'pre',
    ]

    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
        'img': ['src', 'title'],
        'iframe': ['src', 'title', 'width', 'height', 'frameborder', 'allowfullscreen'],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls = type(self)
        # cache renderers
        if not hasattr(cls, 'renderers'):
            cls.renderers = {
                getattr(cls, attr): getattr(cls, 'render_{}'.format(attr.split('_', 1)[-1].lower()))
                for attr in dir(cls) if attr.startswith('RENDERER_')
            }

    def __str__(self):
        return self.title

    @property
    def rendered(self):
        """
        Render article text according to the specified renderer.

        :return: Rendered article text
        """
        try:
            renderer = self.renderers[self.renderer]
        except KeyError:
            logger.error('No article renderer %s', self.renderer)
            renderer = self.renderers[self._meta.get_field('renderer').default]

        return renderer(self.text)

    @classmethod
    def render_plaintext(cls, value):
        return value

    @classmethod
    def render_html(cls, value):
        value = bleach.clean(
            value,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
        )
        return mark_safe(value)

    @classmethod
    def render_markdown(cls, value):
        return cls.render_html(markdown.markdown(escape(value)))
