# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import re
import datetime
import logging
from functools import partial, reduce
import copy

from django.core.urlresolvers import reverse
from django.db import models, transaction, IntegrityError, connection
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils import html
from django.utils.decorators import method_decorator
from django.core.cache import cache as redis

import six
import IPy
import julia
import serverquery
import aggregate_if
from whois import whois

from .utils import lock, force_ipy, calc_ratio
from . import definitions, const, utils, config

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
        'team': ('team', int),
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
    def hostname_clean(self):
        """
        Return the colorless server name.
        """
        return utils.force_clean_name(self.hostname)

    def hostname_colored(self):
        hostname = html.escape(self.hostname)
        # replace [c=xxxxxx] tags with html span tags
        hostname = re.sub(
            r'\[c=([a-f0-9]{6})\](.*?)(?=\[c=([a-f0-9]{6})\]|\[\\c\]|$)', 
            r'<span style="color:#\1;">\2</span>', 
            self.hostname, 
            flags=re.I
        )
        # remove [b], [\b], [u], [\u], [\c] tags
        hostname = re.sub(r'\[(?:\\)?[buc]\]', '', hostname, flags=re.I)
        return html.mark_safe(hostname)

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

    @property
    def time_remaining(self):
        if self.date_updated and self.player_num and self.time:
            return self.time - (timezone.now() - self.date_updated).seconds
        return self.time

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
                logger.warning('failed to parse %s from %s (%s, %s)' % (response, self.server, type(e).__name__, e))
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
        response = serverquery.gamespy1.Server(ip_addr, port, timeout).status()
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
            logger.warning('received empty response from %s:%s' % (ip_addr, port))
        return response


class ServerManager(models.Manager):

    status = ServerStatusManager()

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

        options.update({'ip': ip, 'port': port})
        obj = self.model(**options)
        obj.clean()
        obj.save()
        return obj

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
    key = models.CharField(max_length=32, blank=True)

    enabled = models.BooleanField(default=False)
    streamed = models.BooleanField(default=False)
    listed = models.BooleanField(default=False)
    # query ports
    port_gs1 = models.PositiveIntegerField(null=True, blank=True)
    port_gs2 = models.PositiveIntegerField(null=True, blank=True)
    # ip-based country code
    country = models.CharField(max_length=2, null=True, blank=True)

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
        try:
            status = self.status
            assert status.hostname_clean
        except:
            # fall back to __str__/__unicode__
            return force_text(self)
        else:
            return status.hostname_clean

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
        return '{0.ip}:{0.port}'.format(self)

    def clean(self):
        self.port = int(self.port)
        if not (1 <= self.port <= 65535):
            raise ValidationError(_('Port number must be between 1 and 65535 inclusive.'))
        if self.streamed and not self.key:
            raise ValidationError(_('Server key must not be empty.'))


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
        return  const.EQUIPMENT[force_text(self.name)]


class AliasManager(models.Manager):

    def get_queryset(self):
        return super(AliasManager, self).get_queryset().select_related()

    def match_or_create(self, defaults=None, **kwargs):
        # name is required for a get_or_create call upon AliasManager
        assert('name' in kwargs)
        # use ip for lookup
        ip = kwargs.pop('ip', None)
        # acquire an isp
        if kwargs.get('isp', None) is None and ip:
            kwargs['isp'] = ISP.objects.match_or_create(ip)[0]
        # attempt to match an existing entry by either name or name+isp pair
        try:
            filters = kwargs.copy()
            # replace None with notnull lookup
            if 'isp' in filters and not filters['isp']:
                del filters['isp']
                filters['isp__isnull'] = True
            return (self.get_queryset().get(**filters), False)
        # create a new entry
        except ObjectDoesNotExist:
            with transaction.atomic():
                # get a profile by name and optionally by ip and isp 
                # ISP could as well be empty
                if kwargs.get('profile', None) is None:
                    filters = {
                        'name': kwargs['name'],
                        'isp': kwargs.get('isp', None)
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
        return utils.calc_accuracy(self.weapon_set.all(), self.MIN_AMMO)

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
        return (super(IPManager, self).get_queryset()
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
        obj = (IP.objects
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
                logger.warning('the returned range for {} is too large ({})'
                    .format(ip_address.strNormal(3), length)
                )
                raise ObjectDoesNotExist
            return (matched_obj, False)
        except ObjectDoesNotExist:
                try:
                    data = whois.whois(ip_address.strNormal(3))
                    logger.debug('received whois for {}: {}, {}, {}'
                        .format(
                            ip_address.strNormal(3), 
                            data.get('ipv4range', None), 
                            data.get('orgname', None), 
                            data.get('country', None)
                        )
                    )
                except Exception as e:
                    logger.critical('failed to get whois for {} ({})'.format(ip_address, e))
                    data = {}
                # attempt to unpack ip range tuple
                ipv4range = data.get('ipv4range', None)
                try:
                    ipv4range_from = force_ipy(ipv4range[0])
                    ipv4range_to = force_ipy(ipv4range[1])
                    # range end address must be always greater than the range start address
                    assert ipv4range_from.int() <= ipv4range_to.int()
                    # the ip must fit into the resolved range
                    assert ipv4range_from.int() <= ip_address.int() <= ipv4range_to.int()
                except (IndexError, ValueError, TypeError, AssertionError) as e:
                    logger.warning('whois for {} does not contain a valid range {}'
                        .format(ip_address.strNormal(3), data)
                    )
                    return (None, False)
                # prepare lookup/create data
                items = {}
                if data.get('orgname', None):
                    items['name'] = data['orgname']
                if data.get('country', None):
                    items['country'] = data['country']
                with transaction.atomic():
                    # attempt to insert the ip range details
                    ip_obj, created = IP.objects.get_or_create(
                        range_from=ipv4range_from.int(), 
                        range_to=ipv4range_to.int()
                    )
                    # we performed an extra lookup but it the same ip range was resolved
                    if not created:
                        logger.warning('the range {}-{} already exists'
                            .format(ipv4range_from.strNormal(3), ipv4range_to.strNormal(3))
                        )
                        return (ip_obj.isp, False)
                    # if isp name is empty, return a new entry without further lookup
                    if 'name' not in items:
                        isp = self.get_queryset().create(**items)
                        created = True
                    # otherwise perform a lookup (still with a possibility of creating a brand new object)
                    else:
                        isp, created = (self.get_queryset()
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
            logger.warning('will skip name lookup for {}'.format(kwargs['name']))

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
        if 'name' in kwargs and (not skip_name) and kwargs.get('isp', None):
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
        return (self.get_queryset()
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
    SET_STATS_ALL = 127

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
        id = self.fetch_popular('loadout', year, only=models.Q(vip=False))
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

    def fetch_popular(self, field, year=None, **kwargs):
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
            annotated = (qs
                .values(field)
                .annotate(num=aggregate_if.Count(field, **kwargs))
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
                const.STATS_SCORE, 
                const.STATS_TOP_SCORE,
                const.STATS_TIME,
                const.STATS_GAMES,
                const.STATS_WINS,
                const.STATS_LOSSES,
                const.STATS_DRAWS,
                # const.STATS_SPM,  # calculated manually at the bottom of the method
                # const.STATS_SPR,
            ])
        if options & Profile.SET_STATS_KILLS:
            categories.extend([
                const.STATS_KILLS,
                const.STATS_TOP_KILLS,
                const.STATS_TEAMKILLS,
                const.STATS_ARRESTS,
                const.STATS_TOP_ARRESTS,
                const.STATS_DEATHS,
                const.STATS_SUICIDES,
                const.STATS_ARRESTED,
                const.STATS_KILL_STREAK,
                const.STATS_ARREST_STREAK,
                const.STATS_DEATH_STREAK,
                # ammo bases stats
                const.STATS_AMMO_SHOTS,
                const.STATS_AMMO_HITS,
                const.STATS_AMMO_DISTANCE,
                # const.STATS_AMMO_ACCURACY,  # calculated manually
                # const.STATS_KDR,
            ])
        # VIP Escort stats
        if options & Profile.SET_STATS_VIP:
            categories.extend([
                const.STATS_VIP_ESCAPES,
                const.STATS_VIP_CAPTURES,
                const.STATS_VIP_RESCUES,
                const.STATS_VIP_KILLS_VALID,
                const.STATS_VIP_KILLS_INVALID,
                #const.STATS_VIP_TIMES,
            ])
        # Rapid Deployment stats
        if options & Profile.SET_STATS_RD:
            categories.extend([
                const.STATS_RD_BOMBS_DEFUSED,
            ])
        # Smash and Grab stats
        if options & Profile.SET_STATS_SG:
            categories.extend([
                const.STATS_SG_ESCAPES,
                const.STATS_SG_KILLS,
            ])
        # COOP stats
        if options & Profile.SET_STATS_COOP:
            categories.extend([
                const.STATS_COOP_SCORE,
                const.STATS_COOP_TIME,
                const.STATS_COOP_GAMES,
                const.STATS_COOP_WINS,
                const.STATS_COOP_LOSSES,
                const.STATS_COOP_TEAMKILLS,
                const.STATS_COOP_DEATHS,
                const.STATS_COOP_HOSTAGE_ARRESTS,
                const.STATS_COOP_HOSTAGE_HITS,
                const.STATS_COOP_HOSTAGE_INCAPS,
                const.STATS_COOP_HOSTAGE_KILLS,
                const.STATS_COOP_ENEMY_ARRESTS,
                const.STATS_COOP_ENEMY_INCAPS,
                const.STATS_COOP_ENEMY_KILLS,
                const.STATS_COOP_ENEMY_INCAPS_INVALID,
                const.STATS_COOP_ENEMY_KILLS_INVALID,
                const.STATS_COOP_TOC_REPORTS,
            ])
        aggregated = self.aggregate_player_stats(categories, start, end)
        # Calculate SPM and SPR manually
        if options & Profile.SET_STATS_COMMON:
            # score per minute
            aggregated[const.STATS_SPM] = calc_ratio(
                aggregated[const.STATS_SCORE], aggregated[const.STATS_TIME], min_divisor=Profile.MIN_TIME
            ) * 60
            # score per round
            aggregated[const.STATS_SPR] = calc_ratio(
                aggregated[const.STATS_SCORE], aggregated[const.STATS_GAMES], min_divisor=Profile.MIN_GAMES
            )
        if options & Profile.SET_STATS_KILLS:
            # calculate kills/deaths manually
            aggregated[const.STATS_KDR] = calc_ratio(
                aggregated[const.STATS_KILLS], aggregated[const.STATS_DEATHS], min_divident=self.MIN_KILLS
            )
            # calculate accuracy
            aggregated[const.STATS_AMMO_ACCURACY] = calc_ratio(
                aggregated[const.STATS_AMMO_HITS], aggregated[const.STATS_AMMO_SHOTS], min_divisor=self.MIN_AMMO
            )
        return aggregated

    def aggregate_player_stats(self, stats, start, end):
        aggregates = {
            'game': {
                const.STATS_SCORE: models.Sum('score'),
                const.STATS_TOP_SCORE: models.Max('score'),
                # non-COOP time
                const.STATS_TIME: (
                    aggregate_if.Sum(
                        'time',  
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS)
                    )
                ),
                # non-coop games
                const.STATS_GAMES: (
                    aggregate_if.Count(
                        'game',  
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS),
                        distinct=True
                    )
                ),
                # non-coop wins
                const.STATS_WINS: (
                    aggregate_if.Count(
                        'game',  
                        only=(models.Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SWAT_GAMES) |
                            models.Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SUS_GAMES)),
                        distinct=True
                    )
                ),
                # non-coop losses
                const.STATS_LOSSES: (
                    aggregate_if.Count(
                        'game',  
                        only=(models.Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SUS_GAMES) |
                            models.Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SWAT_GAMES)),
                        distinct=True
                    )
                ),
                # non-coop draws
                const.STATS_DRAWS: (
                    aggregate_if.Count(
                        'game',
                        only=models.Q(
                            game__outcome__in=definitions.DRAW_GAMES, 
                            game__gametype__in=definitions.MODES_VERSUS
                        ),
                        distinct=True
                    )
                ),
                const.STATS_KILLS: models.Sum('kills'),
                const.STATS_TOP_KILLS: models.Max('kills'),
                # non-coop teamkills
                const.STATS_TEAMKILLS: (
                    aggregate_if.Sum(
                        'teamkills',
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS)
                    )
                ),
                const.STATS_ARRESTS: models.Sum('arrests'),
                const.STATS_TOP_ARRESTS: models.Max('arrests'),
                const.STATS_ARRESTED: models.Sum('arrested'),
                # non-coop deaths
                const.STATS_DEATHS: (
                    aggregate_if.Sum(
                        'deaths',
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS)
                    )
                ),
                # non-coop suicides
                const.STATS_SUICIDES: (
                    aggregate_if.Sum(
                        'suicides',
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS)
                    )
                ),
                const.STATS_KILL_STREAK: models.Max('kill_streak'),
                const.STATS_ARREST_STREAK: models.Max('arrest_streak'),
                const.STATS_DEATH_STREAK: (
                    aggregate_if.Max(
                        'death_streak',
                        only=models.Q(game__gametype__in=definitions.MODES_VERSUS)
                    )
                ),
                # VIP Escort stats
                const.STATS_VIP_ESCAPES: models.Sum('vip_escapes'),
                const.STATS_VIP_CAPTURES: models.Sum('vip_captures'),
                const.STATS_VIP_RESCUES: models.Sum('vip_rescues'),
                const.STATS_VIP_KILLS_VALID: models.Sum('vip_kills_valid'),
                const.STATS_VIP_KILLS_INVALID: models.Sum('vip_kills_invalid'),
                const.STATS_VIP_TIMES: (
                    aggregate_if.Count('pk', only=models.Q(vip=True), distinct=True)
                ),
                # Rapid Deployment stats
                const.STATS_RD_BOMBS_DEFUSED: models.Sum('rd_bombs_defused'),
                const.STATS_SG_ESCAPES: models.Sum('sg_escapes'),
                const.STATS_SG_KILLS: models.Sum('sg_kills'),
                # COOP stats
                const.STATS_COOP_SCORE: (
                    aggregate_if.Sum(
                        'game__coop_score', 
                        models.Q(game__gametype__in=definitions.MODES_COOP)
                    )
                ),
                const.STATS_COOP_TIME: (
                    aggregate_if.Sum(
                        'time', 
                        only=models.Q(game__gametype__in=definitions.MODES_COOP)
                    )
                ),
                const.STATS_COOP_GAMES: (
                    aggregate_if.Count(
                        'game', 
                        only=models.Q(game__gametype__in=definitions.MODES_COOP),
                        distinct=True
                    )
                ),
                const.STATS_COOP_WINS: (
                    aggregate_if.Count(
                        'game', 
                        only=models.Q(game__outcome__in=definitions.COMPLETED_MISSIONS),
                        distinct=True
                    )
                ),
                const.STATS_COOP_LOSSES: (
                    aggregate_if.Count(
                        'game', 
                        only=models.Q(game__outcome__in=definitions.FAILED_MISSIONS),
                        distinct=True
                    )
                ),
                const.STATS_COOP_TEAMKILLS: (
                    aggregate_if.Sum(
                        'teamkills', 
                        only=models.Q(game__gametype__in=definitions.MODES_COOP)
                    )
                ),
                const.STATS_COOP_DEATHS: (
                    aggregate_if.Sum(
                        'deaths', 
                        only=models.Q(game__gametype__in=definitions.MODES_COOP)
                    )
                ),
                const.STATS_COOP_HOSTAGE_ARRESTS: models.Sum('coop_hostage_arrests'),
                const.STATS_COOP_HOSTAGE_HITS: models.Sum('coop_hostage_hits'),
                const.STATS_COOP_HOSTAGE_INCAPS: models.Sum('coop_hostage_incaps'),
                const.STATS_COOP_HOSTAGE_KILLS: models.Sum('coop_hostage_kills'),
                const.STATS_COOP_ENEMY_ARRESTS: models.Sum('coop_enemy_arrests'),
                const.STATS_COOP_ENEMY_INCAPS: models.Sum('coop_enemy_incaps'),
                const.STATS_COOP_ENEMY_KILLS: models.Sum('coop_enemy_kills'),
                const.STATS_COOP_ENEMY_INCAPS_INVALID: models.Sum('coop_enemy_incaps_invalid'),
                const.STATS_COOP_ENEMY_KILLS_INVALID: models.Sum('coop_enemy_kills_invalid'),
                const.STATS_COOP_TOC_REPORTS: models.Sum('coop_toc_reports'),
            },
            'weapon': {
                # ammo based stats
                const.STATS_AMMO_SHOTS: (
                    aggregate_if.Sum(
                        'weapon__shots',
                        only=models.Q(
                            weapon__name__in=definitions.WEAPONS_FIRED,
                            game__gametype__in=definitions.MODES_VERSUS
                        )
                    )
                ),
                const.STATS_AMMO_HITS: (
                    aggregate_if.Sum(
                        'weapon__hits',
                        only=models.Q(
                            weapon__name__in=definitions.WEAPONS_FIRED,
                            game__gametype__in=definitions.MODES_VERSUS
                        )
                    )
                ),
                const.STATS_AMMO_DISTANCE: (
                    aggregate_if.Max(
                        'weapon__distance',
                        only=models.Q(
                            weapon__name__in=definitions.WEAPONS_FIRED,
                            game__gametype__in=definitions.MODES_VERSUS
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
            {'shots': models.Sum('weapon__shots'),
            'time': models.Sum('weapon__time'),
            'hits': models.Sum('weapon__hits'),
            'teamhits': models.Sum('weapon__teamhits'),
            'kills': models.Sum('weapon__kills'),
            'teamkills': models.Sum('weapon__teamkills'),
            'distance': models.Max('weapon__distance')}, 
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
            entries = (self.get_queryset()
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
            cursor = connection.cursor()
            try:
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
            finally:
                cursor.close()


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