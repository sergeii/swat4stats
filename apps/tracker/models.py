import re
from datetime import time, datetime
import logging
from collections import namedtuple
from typing import Union

from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, F, When, Case, Count, Func, Expression, Subquery
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.functions import Upper
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from apps.tracker.entities import GameType, Equipment
from apps.tracker.managers import (ServerQuerySet, ServerManager, MapManager,
                                   GameManager, LoadoutManager, AliasManager,
                                   PlayerManager, PlayerQuerySet, ProfileManager,
                                   ProfileQuerySet, StatsManager)
from apps.tracker.schema import teams_reversed
from apps.tracker.templatetags import map_background_picture
from apps.tracker.utils import (force_clean_name, ratio)
from apps.utils.db.fields import EnumField
from apps.utils.misc import force_datetime, dumps

logger = logging.getLogger(__name__)


class Server(models.Model):
    ip = models.GenericIPAddressField(protocol='IPv4')
    port = models.PositiveIntegerField()
    status_port = models.PositiveIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    listed = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    country = models.CharField(max_length=2, null=True, blank=True)
    hostname = models.CharField(max_length=256, null=True, blank=True)
    version = models.CharField(max_length=64, null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=0)

    # pending removal
    port_gs1 = models.PositiveIntegerField(null=True, blank=True)
    port_gs2 = models.PositiveIntegerField(null=True, blank=True)
    streamed = models.BooleanField(default=False)

    objects = ServerManager.from_queryset(ServerQuerySet)()

    class Meta:
        unique_together = (('ip', 'port'),)
        indexes = [
            models.Index(Func(F('ip'), function='host'), F('port'), name='tracker_server_host_ip_port'),
        ]

    @cached_property
    def address(self):
        return f'{self.ip}:{self.port}'

    @cached_property
    def name(self):
        if self.hostname:
            return force_clean_name(self.hostname)
        return self.address

    def clean(self):
        """
        Ensure port is in valid range.

        :raises django.core.exceptions.ValidationError: If port is invalid
        """
        try:
            self.port = int(self.port)
            if not (1 <= self.port <= 65535):
                raise AssertionError
        except (ValueError, AssertionError):
            raise ValidationError(_('Port number must be between 1 and 65535 inclusive.'))

    def update_with_status(self, status: dict[str, str | list[dict[str, str]]]) -> None:
        redis = cache.client.get_client()
        logger.info('storing status for server %s:%s (%s)',
                    self.ip, self.port, self.pk)
        redis.hset(settings.TRACKER_SERVER_REDIS_KEY, self.address, dumps(status).encode())

    def save(self, *args, **kwargs):
        self.clean()
        # set default status port
        if not self.status_port:
            self.status_port = self.port + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Map(models.Model):
    name = models.CharField(max_length=255, unique=True)

    objects = MapManager()

    def __str__(self):
        return self.name

    @cached_property
    def slug(self):
        return slugify(self.name)

    @cached_property
    def preview_picture(self):
        return map_background_picture(self.name, type='preview')

    @cached_property
    def background_picture(self):
        return map_background_picture(self.name, type='background')


class Game(models.Model):
    server = models.ForeignKey('Server', on_delete=models.PROTECT)
    tag = models.CharField(max_length=8, null=True, unique=True)
    time = models.SmallIntegerField(default=0)
    outcome = EnumField(db_column='outcome_enum', enum_type='outcome_enum', null=True)
    outcome_legacy = models.SmallIntegerField(db_column='outcome', default=0)
    gametype = EnumField(db_column='gametype_enum', enum_type='gametype_enum', null=True)
    gametype_legacy = models.SmallIntegerField(db_column='gametype', null=True)
    map = models.ForeignKey('Map', on_delete=models.PROTECT)
    player_num = models.SmallIntegerField(default=0)
    score_swat = models.SmallIntegerField(default=0)
    score_sus = models.SmallIntegerField(default=0)
    vict_swat = models.SmallIntegerField(default=0)
    vict_sus = models.SmallIntegerField(default=0)
    rd_bombs_defused = models.SmallIntegerField(default=0)
    rd_bombs_total = models.SmallIntegerField(default=0)
    coop_score = models.SmallIntegerField(default=0)
    date_finished = models.DateTimeField(default=timezone.now)

    # pending removal
    mapname = models.SmallIntegerField()

    objects = GameManager()

    class Meta:
        indexes = [
            models.Index((F('score_swat') + F('score_sus')).desc(), name='tracker_game_score_swat_score_sus'),
            models.Index(F('date_finished').desc(), name='tracker_game_date_finished_desc'),
        ]

    class DataAlreadySaved(Exception):
        pass

    PlayerHighlight = namedtuple('PlayerHighlight', ['player', 'title', 'description'])

    highlights = [
        (_('Hostage Crisis'), _('%(points)s VIP rescues'), 'vip_rescues', 2),
        (_('No Exit'), _('%(points)s VIP captures'), 'vip_captures', 2),
        (_('Quick Cut'), _('%(points)s bombs defused'), 'rd_bombs_defused', 2),
        (_('Undying'), _('%(points)s enemies killed in a row'), 'kill_streak', 5),
        (_('Insane'), _('%(points)s enemies arrested in a row'), 'arrest_streak', 5),
        (_('Top Gun'), _('%(points)s points earned'), 'score', 30),
        (_('Fire in the hole!'), _('%(points)s%% of grenades hit their targets'), 'grenade_accuracy', 50),
        (_('Sharpshooter'), _('%(points)s%% of all shots hit targets'), 'gun_weapon_accuracy', 25),
        (_('Killing Machine'), _('%(points)s enemies eliminated'), 'kills', 10),
        (_('Resourceful'), _('%(points)s rounds of ammo fired'), 'gun_weapon_shots', 300),
        # COOP
        (_('Entry team to TOC!'), _('%(points)s reports sent to TOC'), 'coop_toc_reports', 10),
        (_('Hostage Crisis'), _('%(points)s civilians rescued'), 'coop_hostage_arrests', 5),
        (_('The pacifist'), _('%(points)s suspects secured'), 'coop_enemy_arrests', 5),
        (_('No Mercy'), _('%(points)s suspects neutralized'), 'coop_enemy_incaps_and_kills', 5),
    ]

    weapon_highlight_min_kills = 5
    weapon_highlight_min_accuracy = 20

    def __str__(self):
        return f'{self.date_finished} - {self.time} - {self.outcome}'

    @cached_property
    def is_coop_game(self):
        return self.gametype in (GameType.co_op, GameType.co_op_qmm)

    def _get_player_highlights(self) -> list[PlayerHighlight]:
        """
        Return a list of notable game achievements credited to specific players.
        """
        items = []
        for title, description, field, min_points in self.highlights:
            top_field_player, points = self._get_player_with_max(field)
            if top_field_player and points >= min_points:
                items.append(
                    Game.PlayerHighlight(
                        player=top_field_player,
                        title=title,
                        description=description % {'points': points},
                    )
                )
        return items + self._get_player_weapon_highlights()

    def _get_player_weapon_highlights(self) -> list[PlayerHighlight]:
        all_player_weapons = {}
        for player in self.player_set.all():
            for wpn in player.gun_weapons:
                if wpn.kills < self.weapon_highlight_min_kills or wpn.accuracy < self.weapon_highlight_min_accuracy:
                    continue
                all_player_weapons.setdefault(wpn.name, []).append((player, wpn))

        highlights = []
        # obtain the highest accuracy among all weapon users
        for weapon_name, weapon_users in all_player_weapons.items():
            top_user, top_user_weapon = max(weapon_users, key=lambda item: item[1].accuracy)
            highlights.append(
                Game.PlayerHighlight(
                    player=top_user,
                    title=_('%(name)s Expert') % {'name': _(weapon_name)},
                    description=_('%(kills)s kills with average accuracy of %(accuracy)s%%' % {
                        'kills': top_user_weapon.kills,
                        'accuracy': top_user_weapon.accuracy,
                    }),
                )
            )

        return highlights

    def _get_player_with_max(self, field) -> tuple[Union['Player', None], int]:
        """
        Return the player with the highest value of given field
        """
        players_with_field = [
            (player, getattr(player, field) or 0) for player in self.player_set.all()
        ]
        top_player_with_score = max(players_with_field, key=lambda item: item[1], default=(None, 0))
        return top_player_with_score


class Loadout(models.Model):
    primary = EnumField(db_column='primary_enum', enum_type='equipment_enum', null=True)
    primary_legacy = models.SmallIntegerField(db_column='primary', default=0)

    primary_ammo = EnumField(db_column='primary_ammo_enum', enum_type='ammo_enum', null=True)
    primary_ammo_legacy = models.SmallIntegerField(db_column='primary_ammo', default=0)

    secondary = EnumField(db_column='secondary_enum', enum_type='equipment_enum', null=True)
    secondary_legacy = models.SmallIntegerField(db_column='secondary', default=0)

    secondary_ammo = EnumField(db_column='secondary_ammo_enum', enum_type='ammo_enum', null=True)
    secondary_ammo_legacy = models.SmallIntegerField(db_column='secondary_ammo', default=0)

    equip_one = EnumField(db_column='equip_one_enum', enum_type='equipment_enum', null=True)
    equip_one_legacy = models.SmallIntegerField(db_column='equip_one', default=0)

    equip_two = EnumField(db_column='equip_two_enum', enum_type='equipment_enum', null=True)
    equip_two_legacy = models.SmallIntegerField(db_column='equip_two', default=0)

    equip_three = EnumField(db_column='equip_three_enum', enum_type='equipment_enum', null=True)
    equip_three_legacy = models.SmallIntegerField(db_column='equip_three', default=0)

    equip_four = EnumField(db_column='equip_four_enum', enum_type='equipment_enum', null=True)
    equip_four_legacy = models.SmallIntegerField(db_column='equip_four', default=0)

    equip_five = EnumField(db_column='equip_five_enum', enum_type='equipment_enum', null=True)
    equip_five_legacy = models.SmallIntegerField(db_column='equip_five', default=0)

    breacher = EnumField(db_column='breacher_enum', enum_type='equipment_enum', null=True)
    breacher_legacy = models.SmallIntegerField(db_column='breacher', default=0)

    head = EnumField(db_column='head_enum', enum_type='equipment_enum', null=True)
    head_legacy = models.SmallIntegerField(db_column='head', default=0)

    body = EnumField(db_column='body_enum', enum_type='equipment_enum', null=True)
    body_legacy = models.SmallIntegerField(db_column='body', default=0)

    objects = LoadoutManager()

    class Meta:
        unique_together = (('primary', 'secondary',
                            'primary_ammo', 'secondary_ammo',
                            'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five',
                            'head', 'body', 'breacher'),)

    def has_armor(self) -> bool:
        return (
            self.head
            and self.body
            and self.head != Equipment.none
            and self.body != Equipment.none
        )


class Weapon(models.Model):
    id = models.BigAutoField('ID', primary_key=True)
    player = models.ForeignKey('Player', on_delete=models.CASCADE,
                               related_name='weapons', related_query_name='weapon')
    name = EnumField(db_column='name_enum', enum_type='equipment_enum', null=True)
    name_legacy = models.SmallIntegerField(db_column='name')
    time = models.SmallIntegerField(default=0)
    shots = models.SmallIntegerField(default=0)
    hits = models.SmallIntegerField(default=0)
    teamhits = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    teamkills = models.SmallIntegerField(default=0)
    distance = models.FloatField(_('Distance, meters'), default=0)

    _grenade_weapons = set(Equipment.grenades())

    @cached_property
    def is_grenade_weapon(self):
        return self.name in self._grenade_weapons

    @cached_property
    def accuracy(self):
        min_shots = settings.TRACKER_MIN_GAME_GRENADES if self.is_grenade_weapon else settings.TRACKER_MIN_GAME_AMMO
        return int(ratio(self.hits, self.shots, min_divisor=min_shots) * 100)


class Alias(models.Model):
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    isp = models.ForeignKey('geoip.ISP', related_name='+', null=True, on_delete=models.PROTECT)

    objects = AliasManager()

    class Meta:
        index_together = (('name', 'isp'),)
        indexes = [
            models.Index(Upper('name'), F('isp_id'), name='tracker_alias_upper_name_isp_id'),
        ]

    def __str__(self):
        return f'{self.name}, {self.isp}'


class Player(models.Model):
    game = models.ForeignKey('Game', on_delete=models.PROTECT)
    alias = models.ForeignKey('Alias', on_delete=models.PROTECT)
    # TODO null to None's
    # TODO: SET NOT NULL
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.PROTECT)
    ip = models.GenericIPAddressField(protocol='IPv4')

    team = EnumField(db_column='team_enum', enum_type='team_enum', null=True)
    team_legacy = models.SmallIntegerField(db_column='team', null=True)
    coop_status = EnumField(db_column='coop_status_enum', enum_type='coop_status_enum', null=True)
    coop_status_legacy = models.SmallIntegerField(db_column='coop_status', default=0)
    vip = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    dropped = models.BooleanField(default=False)

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

    objects = PlayerManager.from_queryset(PlayerQuerySet)()

    _gun_weapon_names = set(Equipment.primary_weapons()) | set(Equipment.secondary_weapons())
    _grenade_weapon_names = set(Equipment.grenades())

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

    @cached_property
    def profile(self):
        return self.alias.profile

    @cached_property
    def name(self):
        return self.alias.name

    @cached_property
    def country(self):
        try:
            return self.alias.isp.country
        except AttributeError:
            return None

    @cached_property
    def special(self):
        return (
            self.vip_escapes +
            self.vip_captures +
            self.vip_rescues +
            self.rd_bombs_defused +
            self.sg_escapes
        )

    @cached_property
    def coop_enemy_incaps_and_kills(self):
        return self.coop_enemy_incaps + self.coop_enemy_kills

    @cached_property
    def gun_weapons(self) -> list[Weapon]:
        return [
            weapon for weapon in self.weapons.all()
            if weapon.name in self._gun_weapon_names
        ]

    @cached_property
    def gun_weapon_shots(self):
        """
        Calculate the number of rounds fired for both primary and secondary weapons.
        """
        shots = 0
        for weapon in self.weapons.all():
            if weapon.name not in self._gun_weapon_names:
                continue
            shots += weapon.shots
        return shots

    @cached_property
    def gun_weapon_accuracy(self) -> int:
        """
        Calculate the average accuracy for all fired weapons,
        excluding some nonlegit weapons such as taser.
        """
        return self._calculate_accuracy(weapon_names=self._gun_weapon_names,
                                        min_shots=settings.TRACKER_MIN_GAME_AMMO)

    @cached_property
    def grenade_accuracy(self) -> int:
        ratio = self._calculate_accuracy(weapon_names=self._grenade_weapon_names,
                                         min_shots=settings.TRACKER_MIN_GAME_GRENADES)
        return min(ratio, 100)

    def _calculate_accuracy(self, *, weapon_names: set, min_shots: int) -> int:
        hits = 0
        shots = 0
        for weapon in self.weapons.all():
            if weapon.name not in weapon_names:
                continue
            hits += weapon.hits
            shots += weapon.shots
        return int(ratio(hits, shots, min_divisor=min_shots) * 100)

    def __str__(self):
        return f'{self.name}, {self.ip}'


class Objective(models.Model):
    id = models.BigAutoField('ID', primary_key=True)
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    name = EnumField(db_column='name_enum', enum_type='objective_enum', null=True)
    name_legacy = models.SmallIntegerField(db_column='name')
    status = EnumField(db_column='status_enum', enum_type='objective_status_enum', null=True)
    status_legacy = models.SmallIntegerField(db_column='status', default=0)

    class Meta:
        pass

    def __str__(self):
        return f'{self.name}, {self.status}'


class Procedure(models.Model):
    id = models.BigAutoField('ID', primary_key=True)
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    name = EnumField(db_column='name_enum', enum_type='procedure_enum', null=True)
    name_legacy = models.SmallIntegerField(db_column='name')
    status = models.CharField(max_length=7)  # xxx/yyy
    score = models.SmallIntegerField(default=0)

    class Meta:
        pass

    def __str__(self):
        return f'{self.name}, {self.score} ({self.status})'


class Profile(models.Model):
    name = models.CharField(max_length=64, null=True)
    team = EnumField(db_column='team_enum', enum_type='team_enum', null=True)
    team_legacy = models.SmallIntegerField(db_column='team', null=True)
    country = models.CharField(max_length=2, null=True)
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.PROTECT)
    game_first = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.PROTECT)
    game_last = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.PROTECT)
    first_seen_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    stats_updated_at = models.DateTimeField(null=True)
    preferences_updated_at = models.DateTimeField(null=True)

    objects = ProfileManager.from_queryset(ProfileQuerySet)()

    def __str__(self):
        return f'{self.name}, {self.country}'

    def fetch_first_preferred_game_id(self) -> int | None:
        # prepare a subquery to get the most recent game ids for the player
        recent_game_ids = (
            Player.objects.using('replica')
            .select_related(None)
            .for_profile(self)
            .order_by('-pk')
            .values_list('game_id', flat=True)
        )[:settings.TRACKER_PREFERRED_GAMES]

        # of the selected games, get the earliest
        least_game_qs = (
            Game.objects.using('replica')
            .filter(pk__in=Subquery(recent_game_ids))
            .only('pk')
            .order_by('pk')
        )[:1]

        try:
            least_recent_game = least_game_qs.get()
        except ObjectDoesNotExist:
            logger.info('least recent game is not available for %s (%s)', self, self.pk)
            return None

        return least_recent_game.pk

    def fetch_preferred_field(
        self,
        field: str,
        count_field: str | Expression | None = None,
        least_game_id: int | None = None,
    ) -> str | int | None:
        """
        Calculate the most popular item for given player field.
        """
        if least_game_id is None:
            least_game_id = self.fetch_first_preferred_game_id()

        if not least_game_id:
            return None

        queryset = (
            Player.objects.using('replica')
            .for_profile(self)
            .filter(game_id__gte=least_game_id)
            .values(field)
            .annotate(num=Count(count_field if count_field else field))
            .order_by('-num')
        )[:1]

        try:
            aggregated = queryset.get()
            return aggregated[field]
        except ObjectDoesNotExist:
            return None

    def fetch_preferred_name(self, least_game_id: int | None = None) -> str | None:
        """Get the most popular name"""
        return self.fetch_preferred_field('alias__name', least_game_id=least_game_id)

    def fetch_preferred_country(self, least_game_id: int | None = None) -> str | None:
        """Get the most recent country"""
        return self.fetch_preferred_field('alias__isp__country', least_game_id=least_game_id)

    def fetch_preferred_team(self, least_game_id: int | None = None) -> str | None:
        """Get the most preferred team"""
        return self.fetch_preferred_field('team', least_game_id=least_game_id)

    def fetch_preferred_loadout(self, least_game_id: int | None = None) -> int | None:
        """Fetch the most preferred non VIP loadout"""
        return self.fetch_preferred_field('loadout_id',
                                          count_field=Case(When(vip=False, then='loadout_id')),
                                          least_game_id=least_game_id)

    def update_preferences(self):
        """
        Update the player's recent preferences
        such as name, team, loadout and country.
        """
        if not (least_game_id := self.fetch_first_preferred_game_id()):
            logger.info('wont update preferences for %s with name=%s team=%s country=%s loadout=%s',
                        self, self.name, self.team, self.country, self.loadout_id)
            return

        logger.info('updating preferences for %s since %d, name=%s team=%s country=%s loadout=%s',
                    self, least_game_id, self.name, self.team, self.country, self.loadout_id)

        self.name = self.fetch_preferred_name(least_game_id) or self.name
        self.country = self.fetch_preferred_country(least_game_id) or self.country
        self.team = self.fetch_preferred_team(least_game_id) or self.team
        self.team_legacy = teams_reversed.get(self.team)
        self.loadout_id = self.fetch_preferred_loadout(least_game_id) or self.loadout_id
        self.preferences_updated_at = timezone.now()

        logger.info('finished updating popular for %s, name=%s team=%s country=%s loadout=%s',
                    self, self.name, self.team, self.country, self.loadout_id)

        self.save(update_fields=['name', 'country', 'team', 'team_legacy', 'loadout_id', 'preferences_updated_at'])

    def update_stats(self) -> None:
        if self.last_seen_at:
            self.update_annual_stats(year=self.last_seen_at.year)
        self.stats_updated_at = timezone.now()
        self.save(update_fields=['stats_updated_at'])

    def update_annual_stats(self, *, year: int) -> None:
        period_from, period_till = Stats.get_period_for_year(year)

        if self.first_seen_at and period_till < self.first_seen_at:
            logger.info('profile %s was first seen %s < %s', self.pk, self.first_seen_at, period_till)
            return

        if self.last_seen_at and period_from > self.last_seen_at:
            logger.info('profile %s was last seen %s > %s', self.pk, self.last_seen_at, period_from)
            return

        logger.info('updating %s stats for profile %s', year, self.pk)

        queryset = (Player.objects
                    .using('replica')
                    .for_profile(self)
                    .with_qualified_games()
                    .for_period(period_from, period_till))

        player_stats = queryset.aggregate_player_stats()
        per_map_stats = queryset.aggregate_stats_by_map()
        per_gametype_stats = queryset.aggregate_stats_by_gametype()
        per_server_stats = queryset.aggregate_stats_by_server()
        per_weapon_stats = queryset.aggregate_stats_by_weapon()

        save_kwargs = {
            'profile': self,
            'year': year,
        }

        with transaction.atomic():
            PlayerStats.objects.save_stats(player_stats, **save_kwargs)
            MapStats.objects.save_grouped_stats(per_map_stats,
                                                grouping_key='map_id',
                                                **save_kwargs)
            GametypeStats.objects.save_grouped_stats(per_gametype_stats,
                                                     grouping_key='gametype',
                                                     **save_kwargs)
            ServerStats.objects.save_grouped_stats(per_server_stats,
                                                   grouping_key='server_id',
                                                   **save_kwargs)
            WeaponStats.objects.save_grouped_stats(per_weapon_stats,
                                                   grouping_key='weapon',
                                                   **save_kwargs)

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
        if len(name) < settings.TRACKER_MIN_NAME_LEN:
            return True
        for pattern in settings.TRACKER_POPULAR_NAMES:
            if re.search(pattern, name, re.I):
                return True
        return False


class Stats(models.Model):
    category = EnumField(enum_type='stats_category_enum')
    year = models.SmallIntegerField()
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    points = models.FloatField(default=0)
    position = models.PositiveIntegerField(null=True, db_index=True)

    @classmethod
    def get_period_for_year(cls, year: int) -> tuple[datetime, datetime]:
        return (force_datetime(datetime(year=year, month=1, day=1)),
                force_datetime(datetime(year=year, month=12, day=31), time.max))

    class Meta:
        abstract = True

    objects = StatsManager()


class PlayerStats(Stats):
    category = EnumField(db_column='category_enum', enum_type='stats_category_enum', null=True)
    category_legacy = models.SmallIntegerField(db_column='category')

    class Meta:
        db_table = 'tracker_rank'
        unique_together = ('year', 'category_legacy', 'profile',)
        indexes = [
            models.Index('year', 'category_legacy',
                         condition=Q(position__lte=5),
                         name='tracker_rank_year_category_position_lte'),
        ]

    grouping_fields = ['category_legacy']
    unique_db_fields = ['year', 'category_legacy', 'profile_id']


class MapStats(Stats):
    map = models.ForeignKey('Map', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('year', 'category', 'profile', 'map',)

    grouping_fields = ['category', 'map_id']
    unique_db_fields = ['year', 'category', 'profile_id', 'map_id']


class GametypeStats(Stats):
    gametype = EnumField(enum_type='gametype_enum')

    class Meta:
        unique_together = ('year', 'category', 'profile', 'gametype',)

    grouping_fields = ['category', 'gametype']
    unique_db_fields = ['year', 'category', 'profile_id', 'gametype']


class ServerStats(Stats):
    server = models.ForeignKey('Server', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('year', 'category', 'profile', 'server',)

    grouping_fields = ['category', 'server_id']
    unique_db_fields = ['year', 'category', 'profile_id', 'server_id']


class WeaponStats(Stats):
    weapon = EnumField(enum_type='equipment_enum')

    class Meta:
        unique_together = ('year', 'category', 'profile', 'weapon',)

    grouping_fields = ['category', 'weapon']
    unique_db_fields = ['year', 'category', 'profile_id', 'weapon']
