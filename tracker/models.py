# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import, division

import re
import datetime
import logging
from functools import partial
import copy

from django.db import models, transaction, connection
from django.db.models import F, Q, When, Case, Value, Count, Sum, Max, Min
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import mark_safe
from django.core.cache import cache as redis

import six
import markdown
import julia
import bleach
from serverquery.protocol import gamespy1
from whois import whois

from .utils import lock, force_ipy, calc_ratio
from . import definitions, const, utils, config
from .definitions import STAT

logger = logging.getLogger(__name__)


class GameMixin(object):

    @property
    def gametype_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'gametype', force_text(self.gametype)
        )

    @property
    def mapname_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'mapname', force_text(self.mapname)
        )


class ServerStatusManager(object):
    STATUS_CACHE_PREFIX = 'server_status'
    STATUS_CACHE_TIMEOUT = 120  # keep cached entries for this number of seconds
                                # if a server went offline this would serve as cache
    # these Status instance attributes are used in cache key construction,
    # the order is important
    STATUS_CACHE_SUFFIX = (
        'player_num', 
        'gametype', 
        'mapname', 
        'gamename', 
        'gamever', 
        'is_empty', 
        'is_full', 
        'passworded',
        'pinned',
    )

    def __init__(self):
        self._set_filters()
        self._set_sortable()

    def __iter__(self):
        return iter(self.get_values(self.keys))

    def __len__(self):
        return len(self.keys)

    def __getitem__(self, key):
        # attempt to return a slice (index)
        try:
            keys = list.__getitem__(self.keys, key)
        # attempt to return a singleton value
        except TypeError:
            # return a cached Status object for specific server
            if isinstance(key, Server):
                keys = redis.keys('%s*' % self.get_cache_key(key))
                try:
                    # return the last cached matching item
                    return list(redis.get_many(keys).values())[-1]
                except IndexError:
                    return None
            # return the cached value as is
            else:
                return redis.get(key)
        else:
            # return as a list
            if isinstance(keys, list):
                return list(self.get_values(keys))
            # fetch the first item
            try:
                # iter because get_values may return a list or a dictview
                # depending on the python version
                return next(iter(self.get_values(keys)))
            except StopIteration:
                return None

    def __setitem__(self, key, value):
        """
        Cache a ServerStatus instance.

        Args:
            key - a Server model instance
            value - a ServerStatus instance
        """
        assert isinstance(key, Server)
        assert isinstance(value, ServerStatus)
        # delete previous entries
        redis.delete_pattern('%s*' % self.get_cache_key(key))
        # append extra key components
        extra = [getattr(value, param) for param in self.STATUS_CACHE_SUFFIX]
        redis.set(self.get_cache_key(key, *extra), value, timeout=self.STATUS_CACHE_TIMEOUT)

    def filter(self, **kwargs):
        clone = self.clone()
        clone._set_filters(**kwargs)
        return clone

    def sort(self, *args):
        clone = self.clone()
        clone._set_sortable(*args)
        return clone

    @property
    def keys(self):
        # map param names to their positions in a cache key
        params = {param: i for i, param in enumerate(self.STATUS_CACHE_SUFFIX)}
        def sort(key):
            # skip prefix, ip, port
            components = key.split(':')[3:]
            comparable = []
            for item, direction in self._sortable:
                value = components[params[item]]
                if direction < 0:
                    # attempt to reverse direction
                    try:
                        value = float(value) * -1
                    except:
                        pass
                # get the param value from the key
                comparable.append(value)
            return comparable
        return sorted(redis.keys(self.get_cache_key_pattern()), key=sort)

    @property
    def values(self):
        return list(self)

    def get_values(self, keys):
        return redis.get_many(keys).values()

    def get_cache_key_pattern(self):
        """
        Return a redis key search pattern according to filters
        """
        # prefix:ip:port:*extra
        return utils.make_cache_key(self.STATUS_CACHE_PREFIX, '*', '*', *self._filters)

    @classmethod
    def get_cache_key(cls, server, *extra):
        """
        Assemble and return the instance status cache key.

        Example:
            server_status:81.19.209.212:10480:*:*:*:
        """
        return utils.make_cache_key(cls.STATUS_CACHE_PREFIX, server.ip, server.port, *extra)

    def clone(self):
        return copy.deepcopy(self)

    def _set_sortable(self, *args):
        sortable = []
        for param in args:
            if param.startswith('-'):
                sortable.append((param[1:], -1))
            else:
                sortable.append((param, 1))
        self._sortable = sortable

    def _set_filters(self, **kwargs):
        filters = []
        for param in self.STATUS_CACHE_SUFFIX:
            try:
                value = kwargs[param]
            except KeyError:
                value = '*'
            filters.append(value)
        self._filters = filters


class ServerStatus(GameMixin):
     # query field map -> instance field, coerce function
    vars_required = {
        'hostname': ('hostname', force_text),
        'gamename': (
            'gamevariant', 
            partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'gamename')
        ),
        'gamever': ('gamever', float),
        'mapname': (
            'mapname', 
            partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'mapname')
        ),
        'gametype': (
            'gametype', 
            partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'gametype')
        ),
        'passworded': ('password', lambda value: value.lower() == 'true'),
        'round_num': ('round', int),
        'round_max': ('numrounds', int),
        'player_num': ('numplayers', int),
        'player_max': ('maxplayers', int),
    }
    # optional vars
    vars_optional = {
        'time': ('timeleft', int),
        'rd_bombs_defused': ('bombsdefused', int),
        'rd_bombs_total': ('bombstotal', int),
        'score_swat': ('swatscore', int),
        'score_sus': ('suspectsscore', int),
        'vict_swat': ('swatwon', int),
        'vict_sus': ('suspectswon', int),
        'tocreports': ('tocreports', force_text),
        'weaponssecured': ('weaponssecured', force_text),
    }
    # instance.players list item variables
    vars_player_required = {
        'name': ('player', force_text),
        'score': ('score', int),
        'ping': ('ping', lambda n: max(0, min(999, int(n)))),
    }
    vars_player_optional = {
        'coop_status': ('coopstatus', int),
        'coop_status_translated': (
            'coopstatus', 
            partial(julia.shortcuts.map, definitions.stream_pattern_node.item('players').item, 'coop_status')
        ),
        'kills': ('kills', int),
        'deaths': ('deaths', int),
        'arrests': ('arrests', int),
        'arrested': ('arrested', int),
        'vip': ('vip', lambda value: bool(int(value))),
        'team': ('team', int),
    }

    # combine requried and optional params
    vars_all = dict(vars_required, **vars_optional)
    vars_player_all = dict(vars_player_required, **vars_player_optional)
    # query timeout
    timeout = 2

    class ResponseError(Exception):
        pass

    def __init__(self, server):
        """
        initialize a server status instance

        Args:
            server - a Server model instance
        """
        self.server = server
        self.date_updated = None
        # initialize response variables
        for attr, (param, coerce) in six.iteritems(self.vars_all):
            setattr(self, attr, None)
        # query the server
        self.query()

    @property
    def pinned(self):
        return int(self.server.pinned)

    @property
    def is_empty(self):
        return not self.player_num

    @property
    def is_full(self):
        return self.player_num == self.player_max

    @property
    def gamename_translated(self):
        """
        Map a SWAT mod name code to a human readable string

        Example:
            0 - SWAT4
            1 - SWAT4X
        """
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'gamename', force_text(self.gamename)
        )

    def query(self):
        """
        Query the server using gamespy1 protocol and sanitize the response. 

        If the server returns nothing or the sanity check fails, raise ResponseError.
        """
        response = self.query_gamespy1_server(self.server.ip, self.server.port_gs1_default, self.timeout)
        if response:
            self.players = []
            self.objectives = []
            try:
                # sanitize status params
                for attr, (param, coerce) in six.iteritems(self.vars_all):
                    # update variables
                    if param in self.vars_required or param in response:
                        # run the assotiated coerce function
                        value = coerce(response[param])
                        # update the attr with the coerced value
                        setattr(self, attr, value)
                # sanitize player params (score, 0 < ping < 999, etc)
                for id, player in six.iteritems(response['players']):
                    item = {
                        'id': id,
                    }
                    for attr, (param, coerce) in six.iteritems(self.vars_player_all):
                        # required or optional
                        if param in self.vars_player_required or param in player:
                            item[attr] = coerce(player[param])
                    # add the player to the list
                    self.players.append(item)
                # sanitize coop objectives
                for objective, status in six.iteritems(response['objectives']):
                    try:
                        # the name has to be detranslated
                        obj_name = julia.shortcuts.unmap(
                            definitions.stream_pattern_node.item('coop_objectives').item, 'name', objective
                        )
                        # map to human readable name
                        obj_status = julia.shortcuts.map(
                            definitions.stream_pattern_node.item('coop_objectives').item, 'status', status
                        )
                    except julia.node.BaseNodeError as e:
                        logger.error(str(e))
                    else:
                        # mimic an Objective instance
                        self.objectives.append({
                            'name': obj_name,
                            'name_translated': objective,
                            'status': status,
                            'status_translated': obj_status,
                        })
            except Exception as e:
                logger.debug('failed to parse %s from %s (%s, %s)' % (response, self.server, type(e).__name__, e))
            else:
                self.date_updated = timezone.now()
                return response
        # if everything else failed, raise an exception
        raise self.ResponseError

    @staticmethod
    def query_gamespy1_server(ip_addr, port, timeout):
        """
        Query a gamespy1 server using provided address details.

        If successful, attempt to parse players and COOP objectives.
        """
        response = gamespy1.Server(ip_addr, port, timeout).status()
        if response:
            response['objectives'] = {}
            response['players'] = {}
            for name, value in six.iteritems(response.copy()):
                # format coop objectives, e.g. "obj_Rescue_All_Hostages"
                matched = re.match(r'^obj_([A-Za-z_]+)$', name)
                if matched:
                    response['objectives'][matched.group(1)] = value
                # format player list
                matched = re.match(r'^([A-Za-z0-9]+)_(\d+)$', name)
                if matched:
                    id = int(matched.group(2))
                    response['players'].setdefault(id, {})
                    response['players'][id][matched.group(1)] = value
        else:
            logger.info('received empty response from %s:%s' % (ip_addr, port))
        return response


class ServerManager(models.Manager):

    status = ServerStatusManager()

    def get_queryset(self, *args, **kwargs):
        return super(ServerManager, self).get_queryset(*args, **kwargs).order_by('-pinned')

    def create_server(self, ip, port, **options):
        """
        Attempt to create a server.
        Raise ValidationError in case of errors.
        """
        try:
            self.get_queryset().get(ip=ip, port=port)
        except ObjectDoesNotExist:
            pass
        else:
            raise ValidationError(_('The server has already been registered.'))

        return self.create(ip=ip, port=port, **options)

    def enabled(self):
        return self.get_queryset().filter(enabled=True)

    def streamed(self):
        return self.enabled().filter(streamed=True)

    def listed(self):
        return self.enabled().filter(listed=True)


@python_2_unicode_compatible
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
        # +custom (HOST(ip), port) index
        unique_together = (('ip', 'port'),)

    @property
    def port_gs1_default(self):
        """
        Return the explicit gamespy1 query port if specified.

        Otherwise, return the default value.
        """
        if not self.port_gs1:
            return self.port + 1
        return self.port_gs1

    @property
    def port_gs2_default(self):
        """
        Return the explicit gamespy2 query port if specified.

        Otherwise, return the default value.
        """
        if not self.port_gs2:
            return self.port + 2
        return self.port_gs2

    @property
    def name(self):
        if self.hostname:
            return utils.force_clean_name(self.hostname)
        return '{0.ip}:{0.port}'.format(self)

    @property
    def status(self):
        """Attempt to retrieve a cached ServerStatus instance."""
        return type(self).objects.status[self]

    def query(self):
        """
        Retrieve the server status by querying it, then cache the instance for further use.
        """
        from . import signals
        try:
            status = ServerStatus(self)
        except Exception as e:
            logger.debug('failed to query %s (%s, %s)' % (self, type(e).__name__, e))
            # emit a failure signal
            signals.query_status_failed.send(sender=None, server=self)
            # reraise the exception, so the caller is notified about the failure
            raise
        else:
            # cache the status instance
            type(self).objects.status[self] = status
            # emit a success signal
            signals.query_status_received.send(sender=None, server=self, status=status)

    def __str__(self):
        return self.name

    def clean(self):
        self.port = int(self.port)
        if not (1 <= self.port <= 65535):
            raise ValidationError(_('Port number must be between 1 and 65535 inclusive.'))

    def save(self, *args, **kwargs):
        """Validate a server instance upon saving."""
        self.clean()
        super(Server, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Game(models.Model, GameMixin):
    # protect game entries from CASCADE DELETE
    server = models.ForeignKey('Server', null=True, on_delete=models.SET_NULL)
    tag = models.CharField(max_length=8, null=True, unique=True)
    time = models.SmallIntegerField(default=0)
    outcome = models.SmallIntegerField(default=0)
    gametype = models.SmallIntegerField(null=True)
    mapname = models.SmallIntegerField(null=True)  # manual index
    player_num = models.SmallIntegerField(default=0)
    score_swat = models.SmallIntegerField(default=0)  # index score_swat + score_sus
    score_sus = models.SmallIntegerField(default=0)
    vict_swat = models.SmallIntegerField(default=0)
    vict_sus = models.SmallIntegerField(default=0)
    rd_bombs_defused = models.SmallIntegerField(default=0)
    rd_bombs_total = models.SmallIntegerField(default=0)
    coop_score = models.SmallIntegerField(default=0)
    # set entry add time automatically
    date_finished = models.DateTimeField(auto_now_add=True)  # manual index

    @property
    def outcome_translated(self):
        """
        Translate the outcome integer code to a human readable name.
        """
        return julia.shortcuts.map(definitions.stream_pattern_node, 'outcome', force_text(self.outcome))

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
            #raise NotImplementedError
        sortable = sorted(sortable, key=utils.sort_key(*comparable), reverse=True)
        return next(iter(sortable), None)

    def __str__(self):
        return '{0.date_finished} - {0.time} - {0.outcome}'.format(self)


class LoadoutManager(models.Manager):

    def get_or_create(self, defaults=None, **kwargs):
        """
        Pass the arguments to the original manager method after performing a couple of checks:
            * Lookup attributes must contain all of the fields. 
              Raise AssertionError in case of afailure

            * At least one of the fields must contain a non-zero (non-empty) loadout item.
              If the check fails, return None without performing a get_or_create call
        """
        # all fields are required for a call
        for field in self.model.FIELDS:
            assert field in kwargs
        # dont create an entry if all of the fields miss an item
        if not any(map(int, kwargs.values())):
            return (None, False)
        return super(LoadoutManager, self).get_or_create(defaults=defaults or {}, **kwargs)


@python_2_unicode_compatible
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

    objects = LoadoutManager()

    def __str__(self):
        # Pepper-ball:Taser Stun Gun, etc
        return ':'.join([
            const.EQUIPMENT[force_text(getattr(self, key))] for key in self.FIELDS
        ])


@python_2_unicode_compatible
class Weapon(models.Model):
    player = models.ForeignKey('Player')
    name = models.SmallIntegerField()
    time = models.SmallIntegerField(default=0)
    shots = models.SmallIntegerField(default=0)
    hits = models.SmallIntegerField(default=0)
    teamhits = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    teamkills = models.SmallIntegerField(default=0)
    distance = models.FloatField(default=0)  # in meters

    def __str__(self):
        # +fix bignum
        return const.EQUIPMENT[force_text(self.name)]


class AliasManager(models.Manager):

    def get_queryset(self):
        return super(AliasManager, self).get_queryset().select_related()

    def match_or_create(self, defaults=None, **kwargs):
        # name is required for a get_or_create call upon AliasManager
        assert('name' in kwargs)
        # use ip for lookup
        ip = kwargs.pop('ip', None)
        # acquire an isp
        if not kwargs.get('isp') and ip:
            kwargs['isp'] = ISP.objects.match_or_create(ip)[0]
        # attempt to match an existing entry by either name or name+isp pair
        filters = kwargs.copy()
        # replace None with notnull lookup
        if 'isp' in filters and not filters['isp']:
            del filters['isp']
            filters['isp__isnull'] = True
        try:
            #return (self.get_queryset().get(**filters), False)
            return (self.get_queryset().filter(**filters)[:1].get(), False)
        # debug
        except MultipleObjectsReturned:
            logger.critical('kwargs: {} filters: {}'.format(kwargs, filters))
        # create a new entry
        except ObjectDoesNotExist:
            with transaction.atomic():
                # get a profile by name and optionally by ip and isp 
                # ISP could as well be empty
                if not kwargs.get('profile'):
                    filters = {
                        'name': kwargs['name'],
                        'isp': kwargs.get('isp')
                    }
                    # ip must not be empty
                    if ip:
                        filters.update({
                            'ip': ip,
                        })
                    kwargs['profile'] = Profile.objects.match_smart_or_create(**filters)[0]
                return (self.get_queryset().create(**kwargs), True)


@python_2_unicode_compatible
class Alias(models.Model):
    profile = models.ForeignKey('Profile')
    name = models.CharField(max_length=64)  # db_index?
    # protect entries from CASCADE DELETE
    isp = models.ForeignKey('ISP', related_name='+', null=True, on_delete=models.SET_NULL)

    objects = AliasManager()

    class Meta:
        # + custom (upper(name), isp_id) index
        index_together = (('name', 'isp'),)

    def __str__(self):
        return '{0.name}, {0.isp}'.format(self)


class PlayerManager(models.Manager):

    def get_queryset(self):
        return (super(PlayerManager, self)
            .get_queryset()
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
            models.Q(
                game__date_finished__gte=start, 
                game__date_finished__lte=end
            ),
            # limit the queryset with the min number of players played in a game
            (models.Q(game__player_num__gte=Profile.MIN_PLAYERS) | 
                # unless its a COOP game
                models.Q(game__gametype__in=definitions.MODES_COOP)
            ),
        ]
        # append extra filters
        if filters:
            args.append(models.Q(**filters))
        return self.filter(*args)


@python_2_unicode_compatible
class Player(models.Model):
    MIN_AMMO = 30  # min ammo required for accuracy calculation

    game = models.ForeignKey('Game')
    alias = models.ForeignKey('Alias')
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.SET_NULL)
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
        # custom (HOST(ip), id DESC) index
        index_together = (
            ('alias', 'score'), 
            ('alias', 'kills'), 
            ('alias', 'arrests'),
            ('alias', 'kill_streak'),
            ('alias', 'arrest_streak'),
            #('alias', 'death_streak'),
        )

    @property
    def profile(self):
        return self.alias.profile

    @property
    def name(self):
        return self.alias.name

    @property
    def country(self):
        return self.alias.isp.country

    @property
    def coop_status_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('players').item, 'coop_status', 
            force_text(self.coop_status)
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
        return '{0.name}, {0.ip}'.format(self)


@python_2_unicode_compatible
class Objective(models.Model):
    game = models.ForeignKey('Game')
    name = models.SmallIntegerField()
    status = models.SmallIntegerField(default=0)

    class Meta:
        # fix bignum
        pass

    @property
    def name_translated(self):
        return utils.map(
            definitions.stream_pattern_node.item('coop_objectives').item, 'name', force_text(self.name)
        )

    @property
    def status_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('coop_objectives').item, 'status', force_text(self.status)
        )

    def __str__(self):
        return '{0.name}, {0.status}'.format(self)


@python_2_unicode_compatible
class Procedure(models.Model):
    game = models.ForeignKey('Game')
    name = models.SmallIntegerField()
    status = models.CharField(max_length=7)  # xxx/yyy
    score = models.SmallIntegerField(default=0)

    class Meta:
        # fix bignum
        pass

    @property
    def name_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('coop_procedures').item, 'name', force_text(self.name)
        )

    def __str__(self):
        return '{0.name}, {0.score} ({0.status})'.format(self)


class IPManager(models.Manager):

    def get_queryset(self):
        """
        Return a queryset with an extra `length` field that
        is equal to the number of ip addresses in the ip range.
        """
        return (
            super(IPManager, self).get_queryset()
            .extra(select={'length': '(range_to - range_from)'})
        )

    def expired(self):
        """
        Return a queryset of IP enties 
        that were created just earlier than IP.TIME_ACTUAL seconds ago.
        """
        return self.get_queryset().filter(date_created__lt=self.model.fetch_min_actual_date())

    def prune_expired(self):
        """Prune no longer actual IP range entries."""
        return self.expired().delete()


@python_2_unicode_compatible
class IP(models.Model):
    TIME_ACTUAL = 3600*24*180  # an ip range will be actual for 6 months

    isp = models.ForeignKey('ISP', null=True)
    range_from = models.BigIntegerField()
    range_to = models.BigIntegerField()
    date_created = models.DateTimeField(auto_now_add=True)

    objects = IPManager()

    class Meta:
        # + custom index
        unique_together = (('range_from', 'range_to'),)

    def is_actual(self):
        """Tell whether an IP entry should be considered actual."""
        return self.date_created > self.fetch_min_actual_date()

    def range_from_normal(self):
        """Return the range start address in dotted form."""
        return force_ipy(self.range_from).strNormal(3)

    def range_to_normal(self):
        """Return the range end address in dotted form."""
        return force_ipy(self.range_to).strNormal(3)

    def length(self, obj):
        return obj.length

    def __str__(self):
        return '%s-%s' % (self.range_from_normal(), self.range_to_normal())

    @classmethod
    def fetch_min_actual_date(cls):
        """Return the min possible relative date for an actual IP range entry."""
        return timezone.now()-datetime.timedelta(seconds=cls.TIME_ACTUAL)

    range_from_normal.admin_order_field = 'range_from'
    range_to_normal.admin_order_field = 'range_to'
    length.admin_order_field = 'length'


class ISPManager(models.Manager):

    def match(self, ip_address):
        """
        Attempt to find an ISP entry matching the provided IP address.

        Return a tuple containing the matched isp object 
        alongside with the number of addresses in the matched ip range .

        Args:
            ip_address - dotted/numeric IP address or a IPy.IP instance 
        """
        # convert to a IPy.IP instance
        ip_address = force_ipy(ip_address)
        # do an inclusive ip lookup
        obj = (
            IP.objects
            .select_related('isp')
            .filter(
                range_from__lte=ip_address.int(), 
                range_to__gte=ip_address.int(),
            )
            .extra(order_by=('length',))[0:1]
            .get()
        )
        return (obj.isp, obj.length)

    def match_or_create(self, ip_address):
        ip_address = force_ipy(ip_address)
        # match against the known networks
        try:
            matched_obj, length = self.match(ip_address)
            # do an extra lookup if the addr num exceedes the limit
            if length > self.model.MAX_LENGTH:
                logger.debug(
                    'the returned range for {} is too large ({})'
                    .format(ip_address.strNormal(3), length)
                )
                raise ObjectDoesNotExist
            return (matched_obj, False)
        except ObjectDoesNotExist:
                try:
                    data = whois.whois(ip_address.strNormal(3))
                    logger.debug(
                        'received whois for {}: {}, {}, {}'
                        .format(ip_address.strNormal(3), data.get('ipv4range'), data.get('orgname'), data.get('country'))
                    )
                except Exception as e:
                    logger.critical('failed to get whois for {} ({})'.format(ip_address, e))
                    data = {}
                # attempt to unpack ip range tuple
                ipv4range = data.get('ipv4range')
                try:
                    ipv4range_from = force_ipy(ipv4range[0])
                    ipv4range_to = force_ipy(ipv4range[1])
                    # range end address must be always greater than the range start address
                    assert ipv4range_from.int() <= ipv4range_to.int()
                    # the ip must fit into the resolved range
                    assert ipv4range_from.int() <= ip_address.int() <= ipv4range_to.int()
                except (IndexError, ValueError, TypeError, AssertionError) as e:
                    logger.warning(
                        'whois for {} does not contain a valid range {}'
                        .format(ip_address.strNormal(3), data)
                    )
                    return (None, False)
                # prepare lookup/create data
                items = {}
                if data.get('orgname'):
                    items['name'] = data['orgname']
                if data.get('country'):
                    items['country'] = data['country']
                with transaction.atomic():
                    # attempt to insert the ip range details
                    ip_obj, created = IP.objects.get_or_create(
                        range_from=ipv4range_from.int(), 
                        range_to=ipv4range_to.int()
                    )
                    # we performed an extra lookup but it the same ip range was resolved
                    if not created:
                        logger.debug(
                            'the range {}-{} already exists'
                            .format(ipv4range_from.strNormal(3), ipv4range_to.strNormal(3))
                        )
                        return (ip_obj.isp, False)
                    # if isp name is empty, return a new entry without further lookup
                    if 'name' not in items:
                        isp = self.get_queryset().create(**items)
                        created = True
                    # otherwise perform a lookup (still with a possibility of creating a brand new object)
                    else:
                        isp, created = (
                            self.get_queryset()
                            .filter(
                                name__isnull=False,
                                country__isnull=('country' not in items)  # country may be null
                            )
                            .get_or_create(**items)
                        )
                    # append the created ip range entry
                    isp.ip_set.add(ip_obj)
                    return (isp, created)


@python_2_unicode_compatible
class ISP(models.Model):
    MAX_LENGTH = 256*256*64  # an extra whois lookup will be performed
                             # in case the existing ip range is too large
                             # for instance, 69.240.0.0-69.245.255.255 is okay
                             # while 77.0.0.0-95.255.255.255 is not

    name = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=2, null=True)
    objects = ISPManager()

    class Meta:
        pass
        #unique_together = (('name', 'country'),)

    def __str__(self):
        return '{0.name}, {0.country}'.format(self)


class ProfileManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super(ProfileManager, self).get_queryset(*args, **kwargs).select_related('game_last')

    def match(self, **kwargs):
        recent = kwargs.pop('recent', False)
        queryset = kwargs.pop('queryset', Alias.objects.all())
        # filter by min played date
        if recent:
            min_date = timezone.now() - datetime.timedelta(seconds=self.model.TIME_RECENT)
            kwargs['player__game__date_finished__gte'] = min_date
        # limit query in case of a lookup different from name+ip pair
        return queryset.select_related('profile').filter(**kwargs)[0:1].get().profile

    def match_recent(self, **kwargs):
        return self.match(recent=True, **kwargs)

    def match_smart(self, **kwargs):
        """
        Attempt to find a profile property of a player in a sequence of steps:

            1.  if `name` and `ip` are provided, perform a `name`+`ip` 
                case insensitive lookup.
            2   if `name` and `isp` are provided and the `isp` is not None, perform a
                `name`+`isp` case-insensitive lookup
            3.  As an extra step also perform a case sensitive lookup for a recently
                created name+non empty country Player entry.
            4.  if `ip` is provided, perform an ip lookup against related Player entries
                that have been created right now or or `Profile.TIME_RECENT` seconds earlier.

        In case neither of the steps return an object, raise a Profile.DoesNotExist exception
        """
        steps = []

        # skip Player, afk and the other popular names
        skip_name = 'name' in kwargs and self.model.is_name_popular(kwargs['name'])

        if skip_name:
            logger.debug('will skip name lookup for {}'.format(kwargs['name']))

        if 'ip' in kwargs:
            if 'name' in kwargs:
                # match a player with a case insensitive lookup unless the name is way too popular
                if not skip_name:
                    steps.append((self.match, {'name__iexact': kwargs['name'], 'player__ip': kwargs['ip']}))
            # isp may as well be None 
            # in that case we should not perform a lookup
            if 'isp' not in kwargs:
                kwargs['isp'] = ISP.objects.match_or_create(kwargs['ip'])[0]

        # isp must not be None for a name+isp lookup
        if 'name' in kwargs and (not skip_name) and kwargs.get('isp'):
            # search for a player by case insensitive name and non-None isp
            steps.append((self.match, {'name__iexact': kwargs['name'], 'isp': kwargs['isp']}))
            # search by name+non-empty country
            if kwargs['isp'].country:
                steps.append((self.match_recent, {'name__iexact': kwargs['name'], 'isp__country': kwargs['isp'].country}))

        if 'ip' in kwargs:
            # search for a player who has recently played with the same ip 
            steps.append((self.match_recent, {'player__ip': kwargs['ip']}))

        for method, attrs in steps:
            try:
                obj = method(**attrs)
            except ObjectDoesNotExist:
                continue
            else:
                logger.debug('found obj with {} by {}'.format(method.__name__, attrs))
                return obj
        # nothing has been found
        raise self.model.DoesNotExist

    def match_smart_or_create(self, **kwargs):
        try:
            return (self.match_smart(**kwargs), False)
        except ObjectDoesNotExist:
            return (super(ProfileManager, self).get_queryset().create(), True)

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


@python_2_unicode_compatible
class Profile(models.Model):
    TIME_RECENT = 3600*24*30*6
    TIME_POPULAR = 3600*24*7
    MIN_KILLS = 500   # min kills required for kd ratio calculation
    MIN_TIME = 60*60*10  # min time for score per minute and other time-based ratio
    MIN_GAMES = 250
    MIN_AMMO = 1000    # min ammo required for accuracy calculation
    MIN_PLAYERS = 10  # min players needed for profile stats 
                      # to be aggregated from the game being quialified
    MIN_NAME_LENGTH = 3  # name with length shorter than this number is considered popular. 

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
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.SET_NULL)

    # reference to the first played game
    game_first = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.SET_NULL)
    # reference to the last played game
    game_last = models.ForeignKey('Game', related_name='+', null=True, on_delete=models.SET_NULL)

    objects = ProfileManager()

    def __str__(self):
        return '{0.name}, {0.country}'.format(self)

    @property
    def popular(self):
        return self.name and (self.team is not None) and self.game_first and self.game_last

    @property
    def first_seen(self):
        try:
            return self.game_first.date_finished
        except:
            return None

    @property
    def last_seen(self):
        try:
            return self.game_last.date_finished
        except:
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
                #STAT.VIP_TIMES,
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
                                Q(game__outcome__in=definitions.DRAW_GAMES, game__gametype__in=definitions.MODES_VERSUS),
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
                                Q(weapon__name__in=definitions.WEAPONS_FIRED, game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__shots'
                            )
                        )
                    )
                ),
                STAT.AMMO_HITS: (
                    Sum(
                        Case(
                            When(
                                Q(weapon__name__in=definitions.WEAPONS_FIRED, game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__hits'
                            )
                        )
                    )
                ),
                STAT.AMMO_DISTANCE: (
                    Max(
                        Case(
                            When(
                                Q(weapon__name__in=definitions.WEAPONS_FIRED, game__gametype__in=definitions.MODES_VERSUS),
                                then='weapon__distance'
                            )
                        )
                    )
                ),
            },
        }
        aggregated = {}
        # remove uninteresting aggregates
        for group, items in six.iteritems(aggregates.copy()):
            for stat in items.copy():
                if not stat in stats:
                    del aggregates[group][stat]
        for items in six.itervalues(aggregates):
            aggregated.update(self.aggregate(items, start, end))
        # convert null values to zeroes
        return {key: value if value else 0 for key, value in six.iteritems(aggregated)}

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
        for key, value in six.iteritems(items.copy()):
            del items[key]
            new_key = force_text(key)
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
            for key, value in six.iteritems(aggregated.copy()):
                del aggregated[key]
                aggregated[keys[key]] = value
        else:
            # skip None entries that were formed thanks to LEFT OUTER JOIN
            aggregated = list(filter(lambda entry: entry[group_by] is not None, aggregated))
            for entry in aggregated:
                for key, value in six.iteritems(entry):
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
        for pattern in config.POPULAR_NAMES:
            if re.search(pattern, name, re.I):
                return True
        return False


class RankManager(models.Manager):

    def get_queryset(self):
        return super(RankManager, self).get_queryset().select_related('profile')

    def numbered(self):
        """
        Return a queryset with an extra field describing positions of the selected rows
        in a unique set of category id of ranking period and sorted in ascending order
        by the number of points earned in the specified period.
        """
        return (self.get_queryset()
            .extra(
                select={
                'row_number': 'ROW_NUMBER() OVER(PARTITION BY %s, %s ORDER BY %s DESC, %s ASC)' %
                    ('category', 'year', 'points', 'id')
                },
            )
            .order_by('row_number')
        )

    def store(self, category, year, profile, points):
        self.store_many({category: points}, year, profile)

    def store_many(self, items, year, profile):
        result = {}
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
            for category, points in six.iteritems(items):
                if points > 0:
                    creatable.append(self.model(profile=profile, year=year, category=category, points=points))
            # bulk insert the categories that are not present in db
            if creatable:
                self.bulk_create(creatable)

    def rank(self, year):
        with transaction.atomic(), lock('EXCLUSIVE', self.model):
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE {table} AS t1 SET position = t2.row_number
                    FROM 
                    (
                        SELECT ROW_NUMBER() OVER(PARTITION BY {0}, {1} ORDER BY {2} DESC, {3} ASC), id 
                        FROM {table}
                    ) AS t2
                    WHERE t1.id=t2.id AND t1.year = %(year)s
                    """.format('category', 'year', 'points', 'id', table=self.model._meta.db_table), 
                    {'year': year}
                )


@python_2_unicode_compatible
class Rank(models.Model):
    category = models.SmallIntegerField()
    year = models.SmallIntegerField()
    profile = models.ForeignKey('Profile')
    points = models.FloatField(default=0)
    position = models.PositiveIntegerField(null=True, db_index=True)
    objects = RankManager()

    class Meta:
        #index_together = (('year', 'category'),)
        unique_together = (('year', 'category', 'profile',),)

    def __str__(self):
        return '{0.year}:{0.category} #{0.position} {0.profile} ({0.points})'.format(self)

    @classmethod
    def get_period_for_now(model):
        """
        Return a 2-tuple of start and end dates for the current year.

        Example:
            (2014-1-1 0:0:0+00, 2014-12-31 23:59:59+00)
        """
        return model.get_period_for_year(int(timezone.now().strftime('%Y')))

    @classmethod
    def get_period_for_year(model, year):
        """
        Return a 2-tuple containing start and end dates 
        for given year number with respect to given date.

        Args:
            year - year number (eg 2014)
        """
        return (
            datetime.datetime(year, 1, 1, tzinfo=timezone.utc), 
            datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

    @classmethod
    def get_period_for_date(model, date):
        """
        Return a 2-tuple containing start and end dates for given date.

        Args:
            date - datetime object
        """
        return model.get_period_for_year(date.year)


class PublishedArticleManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        """
        Return a queryset that would fetch articles with 
        the `date_published` column greater or equal to the current time.
        """
        return (
            super(PublishedArticleManager, self)
            .get_queryset(*args, **kwargs)
            .filter(is_published=True, date_published__lte=timezone.now)
        )

    def latest(self, limit):
        """Display the latest `limit` published articles."""
        return self.get_queryset().order_by('-date_published')[:limit]


@python_2_unicode_compatible
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
        'a',
        'abbr',
        'acronym',
        'b',
        'blockquote',
        'code',
        'em',
        'i',
        'li',
        'ol',
        'strong',
        'ul',
        'img',
        'iframe',
        'p',
        'div',
    ]

    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
        'img': ['src', 'title'],
        'iframe': ['src', 'title', 'width', 'height', 'frameborder', 'allowfullscreen'],
    }

    ALLOWED_STYLES = []


    def __init__(self, *args, **kwargs):
        super(Article, self).__init__(*args, **kwargs)
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
            logger.error('No article renderer {}'.format(self.renderer))
        except KeyError:
            renderer = self.renderers[self._meta.get_field('renderer').default]

        return renderer(self.text)

    @classmethod
    def render_plaintext(cls, value):
        return value

    @classmethod
    def render_html(cls, value):
        value = bleach.clean(
            value, tags=cls.ALLOWED_TAGS, attributes=cls.ALLOWED_ATTRIBUTES, styles=cls.ALLOWED_STYLES,
        )
        return mark_safe(value)

    @classmethod
    def render_markdown(cls, value):
        return cls.render_html((markdown.markdown(value)))
