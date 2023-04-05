import datetime
import logging

import pytz
from django.db import models
from django.db.models import Q, When, Case, Count, Sum, Max, Func, F
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Upper
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from vendor.julia import shortcuts as julia_shortcuts

from .utils import force_ipy, calc_ratio
from . import definitions, const, utils

logger = logging.getLogger(__name__)


class GameMixin:

    @property
    def gametype_translated(self):
        return julia_shortcuts.map(
            definitions.stream_pattern_node, 'gametype', str(self.gametype)
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

    def __str__(self):
        return f'{self.ip}:{self.port}'


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
    def date_started(self):
        """
        Calculate and return the date of the game start based on the game duration.
        """
        return self.date_finished - datetime.timedelta(seconds=self.time)

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
    def coop_score_normal(self):
        """
        Normalize the COOP (>=0, <=100) score and return the result.
        """
        return max(0, min(100, self.coop_score))

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
        return julia_shortcuts.map(
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
    def status_translated(self):
        return julia_shortcuts.map(
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

    def range_to_normal(self):
        """Return the range end address in dotted form."""
        return force_ipy(self.range_to).strNormal(3)

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

    def fetch_popular_loadout(self, year=None):
        """Return the profile's most popular loadout."""
        # skip the VIP's loadout
        id = self.fetch_popular('loadout', year, Case(When(vip=False, then='loadout')))
        if id:
            return Loadout.objects.get(pk=id)
        return None

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


class RankManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('profile')


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

    def __str__(self):
        return self.title
