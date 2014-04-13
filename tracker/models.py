# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import re
import datetime
import logging
from functools import partial

from django.core.urlresolvers import reverse
from django.db import models, transaction, IntegrityError, connection
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.decorators import method_decorator

import six
import IPy
import julia
import cacheops
import aggregate_if
from whois import whois

from .utils import lock, force_ipy, calc_ratio
from . import definitions, const, utils

logger = logging.getLogger(__name__)


class GameMixin(models.Model):
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

    class Meta:
        abstract = True

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


class PlayerMixin(models.Model):
    profile = models.ForeignKey('Profile')
    team = models.SmallIntegerField(default=-1)
    vip = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    dropped = models.BooleanField(default=False)
    coop_status = models.SmallIntegerField(default=0)

    class Meta:
        abstract = True


class ServerManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super(ServerManager, self).get_queryset(*args, **kwargs).select_related('status')

    def enabled(self):
        return self.get_queryset().filter(enabled=True)


@python_2_unicode_compatible
class Server(models.Model):
    ip = models.GenericIPAddressField(protocol='IPv4')
    port = models.PositiveSmallIntegerField()
    key = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)

    objects = ServerManager()

    class Meta:
        unique_together = (('ip', 'port'),)

    @property
    def name(self):
        try:
            return self.status.hostname
        except:
            return '{0.ip}:{0.port}'.format(self)

    def __str__(self):
        return self.name


class ServerStatusManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super(ServerStatusManager, self).get_queryset(*args, **kwargs).select_related('server')

    def online(self):
        min_date = timezone.now() - datetime.timedelta(seconds=self.model.TIME_ONLINE)
        return self.get_queryset().filter(date_updated__gte=min_date)


@python_2_unicode_compatible
class ServerStatus(GameMixin):
    TIME_ONLINE = 60  # time since the last update a server will be considered online
    # query field map -> model field, coerce
    VARS_REQUIRED = {
        'hostname': ('hostname', force_text),
        'gamevariant': ('gamename', partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'gamename')),
        'gamever': ('gamever', force_text),
        'mapname': ('mapname', partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'mapname')),
        'gametype': ('gametype', partial(julia.shortcuts.unmap, definitions.stream_pattern_node, 'gametype')),
        'password': ('passworded', lambda value: value.lower() == 'true'),
        'round': ('round_num', int),
        'numrounds': ('round_max', int),
        'numplayers': ('player_num', int),
        'maxplayers': ('player_max', int),
        'timeleft': ('time', int),
        'swatscore': ('score_swat', int),
        'suspectsscore': ('score_sus', int),
        'swatwon': ('vict_swat', int),
        'suspectswon': ('vict_sus', int),
    }
    # optional vars
    VARS_OPTIONAL = {
        'bombsdefused': ('rd_bombs_defused', int),
        'numbombs': ('rd_bombs_total', int),
    }

    server = models.OneToOneField('Server', related_name='status')
    gamename = models.SmallIntegerField(null=True)
    gamever = models.CharField(max_length=5, null=True)
    hostname = models.CharField(max_length=255, null=True)
    passworded = models.BooleanField(default=False)
    round_num = models.SmallIntegerField(default=0)
    round_max = models.SmallIntegerField(default=0)
    player_max = models.SmallIntegerField(default=0)
    time = models.SmallIntegerField(null=True)
    date_updated = models.DateTimeField(auto_now=True)

    objects = ServerStatusManager()

    def __str__(self):
        return self.hostname

    @property
    def gamename_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node, 'gamename', force_text(self.gamename)
        )

    @property
    def time_remaining(self):
        if self.date_updated and self.player_count:
            return self.time - (timezone.now() - self.date_updated).seconds
        return self.time

    def query_status(self):
        @cacheops.cached(timeout=5, extra=self.pk)
        def _query_status():
            import serverquery
            response = serverquery.gamespy1.Server(self.server.ip, port=self.server.port + 1).status()
            if response:
                # check the required params
                try:
                    for key in self.VARS_REQUIRED:
                        assert key in response, '%s is missing in a response' % key
                except Exception as e:
                    logger.critical(e)
                else:
                    # combine requried and optional params
                    combined = self.VARS_REQUIRED.copy()
                    combined.update(self.VARS_OPTIONAL)
                    try:
                        for key, (attr, coerce) in six.iteritems(combined):
                            # update variables
                            if key in response:
                                value = coerce(response[key])
                                # set attr
                                setattr(self, attr, value)
                                # update the dict value as well
                                if attr in response:  # this will be overwritten
                                    response['_%s' % key] = response[key]
                                response[attr] = value
                    except Exception as e:
                        logger.critical(e)
                    else:
                        self.save()
                        return response
            return None
        status = _query_status()
        # invalidate cache in case of invalid status
        if not status:
            _query_status.invalidate()
        return status


class PlayerManager(models.Manager):

    def get_queryset(self):
        return super(PlayerManager, self).get_queryset().select_related('profile', 'alias', 'alias__isp')

    def prefetched(self):
        return self.get_queryset().prefetch_related('score_set', 'weapon_set')


@python_2_unicode_compatible
class PlayerStatus(PlayerMixin):
    server = models.ForeignKey('Server')
    score = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    deaths = models.SmallIntegerField(default=0)
    arrests = models.SmallIntegerField(default=0)
    arrested = models.SmallIntegerField(default=0)
    special = models.SmallIntegerField(default=0)

    objects = PlayerManager()

    def __str__(self):
        return '{0.name} {0.ip}'.format(self)


@python_2_unicode_compatible
class Game(GameMixin):
    # protect game entries from CASCADE DELETE
    server = models.ForeignKey('Server', null=True, on_delete=models.SET_NULL)
    tag = models.CharField(max_length=8, null=True, unique=True)
    time = models.SmallIntegerField(default=0)
    outcome = models.SmallIntegerField(default=0)
    # set entry add time automatically
    date_finished = models.DateTimeField(auto_now_add=True)

    @property
    def outcome_translated(self):
        return julia.shortcuts.map(definitions.stream_pattern_node, 'outcome', force_text(self.outcome))

    @property
    def date_started(self):
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
        "Tell whether this was a COOP game."
        assert isinstance(self.gametype, int)
        if self.gametype in definitions.MODES_COOP:
            return True
        return False

    @property
    def coop_successful(self):
        "Tell whether the COOP game was successful."
        assert isinstance(self.outcome, int)
        if self.outcome in definitions.COMPLETED_MISSIONS:
            return True
        elif self.outcome in definitions.FAILED_MISSIONS:
            return False
        return None

    @property
    def coop_score_normal(self):
        return max(0, min(100, self.coop_score))

    def __str__(self):
        return '{0.date_finished} - {0.time} - {0.outcome}'.format(self)


class LoadoutManager(models.Manager):

    def get_or_create(self, defaults=None, **kwargs):
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
        # Pepper-ball::Taser Stun Gun, etc
        return '::'.join([
            const.EQUIPMENT[force_text(getattr(self, key))] for key in (
                'primary', 'secondary', 'head', 'body',
                'breacher', 'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five'
            )
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
        return  const.EQUIPMENT[force_text(self.name)]


@python_2_unicode_compatible
class Score(models.Model):
    player = models.ForeignKey('Player')
    category = models.SmallIntegerField()
    points = models.SmallIntegerField()

    class Meta:
        pass

    def __str__(self):
        return '{0.category}/{0.points} {0.player_id}'.format(self)


class AliasManager(models.Manager):

    def get_or_create(self, defaults=None, **kwargs):
        @cacheops.cached(timeout=60*60)
        def _alias_manager_get_or_create(defaults, **kwargs):
            # name and ip are required for a get_or_create call upon the AliasManager
            assert('name' in kwargs)
            assert('ip' in kwargs)
            # attempt to match an existing entry
            try:
                return (self.get_queryset().get(**kwargs), False)
            # create a new entry
            except ObjectDoesNotExist:
                with transaction.atomic():
                    # get an appropriate isp matching the given ip
                    if kwargs.get('isp', None) is None:
                        kwargs['isp'] = ISP.objects.match_or_create(kwargs['ip'])[0]
                return (self.get_queryset().create(**kwargs), True)
        return _alias_manager_get_or_create(defaults, **kwargs)


@python_2_unicode_compatible
class Alias(models.Model):
    name = models.CharField(max_length=64)
    ip = models.GenericIPAddressField(protocol='IPv4')
    # protect entries from CASCADE DELETE
    isp = models.ForeignKey('ISP', related_name='+', null=True, on_delete=models.SET_NULL)

    objects = AliasManager()

    class Meta:
        index_together = (('name', 'ip'), ('name', 'isp'))

    def __str__(self):
        return '{0.name} ({0.ip})'.format(self)


@python_2_unicode_compatible
class Player(PlayerMixin):
    MIN_AMMO = 30  # min ammo required for accuracy calculation

    game = models.ForeignKey('Game')
    alias = models.ForeignKey('Alias')
    loadout = models.ForeignKey('Loadout', null=True, on_delete=models.SET_NULL)

    objects = PlayerManager()

    @property
    def name(self):
        return self.alias.name

    @property
    def ip(self):
        return self.alias.ip

    @property
    def country(self):
        return self.alias.isp.country

    @property
    def coop_status_translated(self):
        return julia.shortcuts.map(
            definitions.stream_pattern_node.item('players').item, 'coop_status', 
            force_text(self.coop_status)
        )

    def __getattr__(self, name):
        """
        Attempt to return a Score value for the given attribute name.

        Args:
            name - a score stat name (e.g. vip_escapes)
        """
        try:
            return self.get_score(
                {value: key for key, value in definitions.STATS}[name]
            )
        except KeyError:
            raise AttributeError

    @property
    def special(self):
        return (
            self.get_score(const.STATS_VIP_ESCAPES) + 
            self.get_score(const.STATS_VIP_CAPTURES) +
            self.get_score(const.STATS_VIP_RESCUES) +
            self.get_score(const.STATS_RD_BOMBS_DEFUSED) +
            self.get_score(const.STATS_SG_ESCAPES)
        )

    @property
    def accuracy(self):
        return utils.calc_accuracy(self.weapon_set.all(), self.MIN_AMMO)

    def get_score(self, category):
        "Best to be used with PlayerManager."
        category = int(category)
        for score in self.score_set.all():
            if score.category == category:
                return score.points
        return 0

    def __str__(self):
        return '{0.name}, {0.ip}'.format(self)

    @staticmethod
    def profile_alias(name, ip, isp=None):
        kwargs = locals()
        if not kwargs['isp']:
            kwargs.pop('isp')
        # name, ip[, isp]
        alias = Alias.objects.get_or_create(**kwargs)[0]
        # + alias
        profile = Profile.objects.match_smart_or_create(**{
            'alias': alias, 
            'name': name, 
            'ip': ip, 
            'isp': alias.isp,
        })
        return {'alias': alias, 'profile': profile[0]}


@python_2_unicode_compatible
class Objective(models.Model):
    game = models.ForeignKey('Game')
    name = models.SmallIntegerField()
    status = models.SmallIntegerField(default=0)

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
        return '{0.range_from}-{0.range_to}'.format(self)

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
        return super(ProfileManager, self).get_queryset(*args, **kwargs).select_related('loadout')

    def match(self, **kwargs):
        recent = kwargs.pop('recent', False)
        queryset = kwargs.pop('queryset', Player.objects.all())
        # filter outdated entries
        if recent:
            min_date = timezone.now() - datetime.timedelta(seconds=self.model.TIME_RECENT)
            kwargs['game__date_finished__gte'] = min_date
        # limit query in case of a lookup different from name+ip pair
        return (queryset.select_related('profile')
            .filter(**kwargs)
            # get the most recent entry
            .order_by('-pk')[0:1]
            .get()
        ).profile

    def match_recent(self, **kwargs):
        return self.match(recent=True, **kwargs)

    def match_smart(self, **kwargs):
        """
        Attempt to find a profile property of a player in a sequence of steps:

            1.  if `alias` is provided, perform an index-frindly alias lookup
            2.  if `name` and `ip` are provided, perform a `name`+`ip` 
                case insensitive lookup.
            3   if `name` and `isp` are provided and the `isp` is not None, perform a
                `name`+`isp` case-insensitive lookup
            4.  As an extra step also perform a case sensitive lookup for a recently
                created name+non empty country Player entry.
            5.  if `ip` is provided, perform an ip lookup against related Player entries
                that have been created right now or or `Profile.TIME_RECENT` seconds earlier.

        In case neither of the steps return an object, raise a Profile.DoesNotExist exception
        """
        steps = []

        # skip Player, afk, etc
        skip_name = 'name' in kwargs and self.model.is_name_popular(kwargs['name'])

        if skip_name:
            logger.warning('will skip name lookups for {}'.format(kwargs['name']))

        # alias lookup
        if 'alias' in kwargs:
            steps.append((self.match, {'alias': kwargs['alias']}))

        if 'ip' in kwargs:
            if 'name' in kwargs:
                # match a player with a case insensitive lookup unless the name is way too popular
                if not skip_name:
                    steps.append((self.match, {'alias__name__iexact': kwargs['name'], 'alias__ip': kwargs['ip']}))
            # isp may as well be None but we should not perform a lookup in such a case
            if 'isp' not in kwargs:
                kwargs['isp'] = ISP.objects.match_or_create(kwargs['ip'])[0]

        # isp is must not be None
        if 'name' in kwargs and (not skip_name) and kwargs.get('isp', None):
            # search for a player by case insensitive name and non-None isp
            steps.append((self.match, {'alias__name__iexact': kwargs['name'], 'alias__isp': kwargs['isp']}))
            # search by a recently used name+non-empty country
            if kwargs['isp'].country:
                steps.append((self.match_recent, {'alias__name__iexact': kwargs['name'], 'alias__isp__country': kwargs['isp'].country}))

        if 'ip' in kwargs:
            # search for a player who has played with the same ip 
            # in the last Profile.TIME_RECENT seconds
            steps.append((self.match_recent, {'alias__ip': kwargs['ip']}))

        for method, attrs in steps:
            try:
                obj = method(**attrs)
            except ObjectDoesNotExist:
                continue
            else:
                logger.debug('successfully found obj with {} by {}'.format(method.__name__, attrs))
                return obj
        raise self.model.DoesNotExist()

    def match_smart_or_create(self, **kwargs):
        @cacheops.cached(timeout=60*60)
        def _profile_manager_match_smart_or_create(**kwargs):
            try:
                return (self.match_smart(**kwargs), False)
            except ObjectDoesNotExist:
                return (super(ProfileManager, self).get_queryset().create(), True)
        return _profile_manager_match_smart_or_create(**kwargs)

    def popular(self):
        return (self.get_queryset()
            .filter(name__isnull=False, team__isnull=False, loadout__isnull=False, date_played__isnull=False)
        )


@python_2_unicode_compatible
class Profile(models.Model):
    TIME_RECENT = 3600*24*60
    TIME_POPULAR = 3600*24*7
    MIN_KILLS = 500   # min kills required for kd ratio calculation
    MIN_SCORE = 2000  # min score for score based ratio stats (spr, spm)
    MIN_AMMO = 250    # min ammo required for weapon accuracy stats
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

    date_played = models.DateTimeField(null=True)
    date_viewed = models.DateTimeField(null=True)

    count_views = models.PositiveIntegerField(default=0)

    objects = ProfileManager()

    def __str__(self):
        return '{0.name}, {0.country}'.format(self)

    @property
    def popular(self):
        return self.name and (self.team is not None) and self.loadout and self.date_played

    @property
    def first_seen(self):
        return self.fetch_first_seen()

    @property
    def last_seen(self):
        return self.date_played

    def fetch_first_seen(self):
        return self.player_set.aggregate(date=models.Min('game__date_finished'))['date']

    def fetch_last_seen(self):
        return self.player_set.aggregate(date=models.Max('game__date_finished'))['date']

    def fetch_popular_name(self):
        """Return the profile's most popular name."""
        return self.fetch_popular('alias__name')

    def fetch_popular_country(self):
        """Return the profile's most popular country."""
        return self.fetch_popular('alias__isp__country')

    def fetch_popular_team(self):
        """Return the profile's most popular team."""
        return self.fetch_popular('team')

    def fetch_popular_loadout(self):
        """Return the profile's most popular loadout."""
        # skip the VIP's loadout
        id = self.fetch_popular('loadout', only=models.Q(vip=False))
        if id:
            return Loadout.objects.get(pk=id)
        return None

    def update_popular(self, save=False):
        self.name = self.fetch_popular_name()
        self.team = self.fetch_popular_team()
        self.country = self.fetch_popular_country()
        self.loadout = self.fetch_popular_loadout()
        if save:
            self.save()

    def fetch_popular(self, field, **kwargs):
        """
        Return a profile's most popular item described 
        by the `field` name of the related Player entries.

        Item popularity is calculated by aggregating on the number
        of games played in the last Profile.TIME_POPULAR seconds and grouping by `field`.
        The topmost record is assumed to be the most popular item.

        Args:
            field - a GROUP BY field
            only - an optional conditional Q object
        """
        try:
            annotated = (self._qualified_popular()
                .values(field)
                .annotate(num=aggregate_if.Count(field, **kwargs))
                .order_by('-num')[0:1]
                .get()
            )
        except ObjectDoesNotExist:
            logger.debug('failed to retrieve popular {} for {}'.format(field, self))
            return None
        else:
            logger.debug('{}\'s {} is {} ({} players)'.format(
                    self, field, annotated[field], annotated['num']
                )
            )
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
            ])
        if options & Profile.SET_STATS_KILLS:
            categories.extend([
                const.STATS_KILLS,
                const.STATS_TEAMKILLS,
                const.STATS_ARRESTS,
                const.STATS_DEATHS,
                const.STATS_ARRESTED,
                const.STATS_KILL_STREAK,
                const.STATS_ARREST_STREAK,
                const.STATS_DEATH_STREAK,
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
                aggregated[const.STATS_SCORE], aggregated[const.STATS_TIME], Profile.MIN_SCORE
            ) * 60
            # score per round
            aggregated[const.STATS_SPR] = calc_ratio(
                aggregated[const.STATS_SCORE], aggregated[const.STATS_GAMES], Profile.MIN_SCORE
            )
        # Calculate kills/deaths manually
        if options & Profile.SET_STATS_KILLS:
            # kills/deaths ratio
            aggregated[const.STATS_KDR] = calc_ratio(
                aggregated[const.STATS_KILLS], aggregated[const.STATS_DEATHS], self.MIN_KILLS
            )
        return aggregated

    def aggregate_player_stats(self, categories, start, end):
        stats = {
            # common stats{
            const.STATS_SCORE: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_SCORE)
                )
            ),
            const.STATS_TOP_SCORE: (
                aggregate_if.Max(
                    'score__points',
                    models.Q(score__category=const.STATS_SCORE)
                )
            ),
            const.STATS_TIME: (
                aggregate_if.Sum(
                    'score__points', 
                    models.Q(
                        score__category=const.STATS_TIME,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            const.STATS_GAMES: (
                aggregate_if.Count(
                    'game', 
                    only=models.Q(game__gametype__in=definitions.MODES_VERSUS),
                    distinct=True
                )
            ),
            const.STATS_WINS: (
                aggregate_if.Count(
                    'game', 
                    only=(models.Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SWAT_GAMES) |
                        models.Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SUS_GAMES)),
                    distinct=True
                )
            ),
            const.STATS_LOSSES: (
                aggregate_if.Count(
                    'game', 
                    only=(models.Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SUS_GAMES) |
                        models.Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SWAT_GAMES)),
                    distinct=True
                )
            ),
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
            # Kill/arrest/death stats
            const.STATS_KILLS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_KILLS)
                )
            ),
            const.STATS_TEAMKILLS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(
                        score__category=const.STATS_TEAMKILLS,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            const.STATS_ARRESTS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_ARRESTS)
                )
            ),
            const.STATS_ARRESTED: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_ARRESTED)
                )
            ),
            const.STATS_DEATHS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(
                        score__category=const.STATS_DEATHS, 
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            const.STATS_KILL_STREAK: (
                aggregate_if.Max(
                    'score__points',
                    models.Q(score__category=const.STATS_KILL_STREAK)
                )
            ),
            const.STATS_ARREST_STREAK: (
                aggregate_if.Max(
                    'score__points',
                    models.Q(score__category=const.STATS_ARREST_STREAK)
                )
            ),
            const.STATS_DEATH_STREAK: (
                aggregate_if.Max(
                    'score__points',
                    models.Q(
                        score__category=const.STATS_DEATH_STREAK,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            # VIP Escort stats
            const.STATS_VIP_ESCAPES: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_VIP_ESCAPES)
                )
            ),
            const.STATS_VIP_CAPTURES: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_VIP_CAPTURES)
                )
            ),
            const.STATS_VIP_RESCUES: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_VIP_RESCUES)
                )
            ),
            const.STATS_VIP_KILLS_VALID: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_VIP_KILLS_VALID)
                )
            ),
            const.STATS_VIP_KILLS_INVALID: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_VIP_KILLS_INVALID)
                )
            ),
            const.STATS_VIP_TIMES: (
                aggregate_if.Count(
                    'player', only=models.Q(vip=True), distinct=True
                )
            ),
            # Rapid Deployment stats
            const.STATS_RD_BOMBS_DEFUSED: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_RD_BOMBS_DEFUSED)
                )
            ),
            const.STATS_SG_ESCAPES: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_SG_ESCAPES)
                )
            ),
            const.STATS_SG_KILLS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_SG_KILLS)
                )
            ),
            # COOP stats
            const.STATS_COOP_SCORE: (
                aggregate_if.Sum(
                    'game__coop_score', 
                    models.Q(game__gametype__in=definitions.MODES_COOP)
                )
            ),
            const.STATS_COOP_TIME: (
                aggregate_if.Sum(
                    'score__points', 
                    models.Q(
                        score__category=const.STATS_TIME,
                        game__gametype__in=definitions.MODES_COOP
                    )
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
                    'score__points', 
                    models.Q(
                        score__category=const.STATS_TEAMKILLS,
                        game__gametype__in=definitions.MODES_COOP
                    )
                )
            ),
            const.STATS_COOP_DEATHS: (
                aggregate_if.Sum(
                    'score__points', 
                    models.Q(
                        score__category=const.STATS_DEATHS,
                        game__gametype__in=definitions.MODES_COOP
                    )
                )
            ),
            const.STATS_COOP_HOSTAGE_ARRESTS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_HOSTAGE_ARRESTS)
                )
            ),
            const.STATS_COOP_HOSTAGE_HITS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_HOSTAGE_HITS)
                )
            ),
            const.STATS_COOP_HOSTAGE_INCAPS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_HOSTAGE_INCAPS)
                )
            ),
            const.STATS_COOP_HOSTAGE_KILLS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_HOSTAGE_KILLS)
                )
            ),
            const.STATS_COOP_ENEMY_ARRESTS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_ENEMY_ARRESTS)
                )
            ),
            const.STATS_COOP_ENEMY_INCAPS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_ENEMY_INCAPS)
                )
            ),
            const.STATS_COOP_ENEMY_KILLS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_ENEMY_KILLS)
                )
            ),
            const.STATS_COOP_ENEMY_INCAPS_INVALID: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_ENEMY_INCAPS_INVALID)
                )
            ),
            const.STATS_COOP_ENEMY_KILLS_INVALID: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_ENEMY_KILLS_INVALID)
                )
            ),
            const.STATS_COOP_TOC_REPORTS: (
                aggregate_if.Sum(
                    'score__points',
                    models.Q(score__category=const.STATS_COOP_TOC_REPORTS)
                )
            ),
        }
        items = {}
        for category in categories:
            items[category] = stats[category]
        # get the stats
        aggregated = self.aggregate(items, start, end)
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
            filters=filters,
        )
        weapons = {}
        for entry in aggregated:
            # calculate accuracy manually
            entry['accuracy'] = calc_ratio(entry['hits'], entry['shots'], min_divisor=self.MIN_AMMO)
            # group by weapon name
            weapons[entry['name']] = entry
        return weapons

    def aggregate(self, items, start, end, group_by=None, filters=None):
        """
        Perform an aggregation over fields defined in `items`.
        Aggregation is done in respect to _qualified query set.

        Args:
            items - aggregates dictionary
            start, end - start and end dates
            group_by - GROUP BY field
                Result is a list of aggregates performed against the field grouped by values.
        """
        keys = {}
        # force dict keys to be strings
        for key, value in six.iteritems(items.copy()):
            del items[key]
            new_key = force_text(key)
            items[new_key] = value
            keys[new_key] = key

        qs = self._qualified_stats(start, end)
        # apply filters
        if filters:
            qs = qs.filter(**filters)
        # annotate
        if group_by:
            aggregated = qs.values(group_by).annotate(**items)
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
                # replace dashed names with the last piece of the name e.g. weapon__name -> name
                val = entry[group_by]
                del entry[group_by]
                entry[group_by.split('__')[-1]] = val
        return aggregated

    def _qualified_popular(self):
        """
        Return a player_set queryset filtered by date of assotiated recently played games.
        """
        return self.player_set.filter(
            game__date_finished__gte=timezone.now()-datetime.timedelta(seconds=Profile.TIME_POPULAR)
        )

    def _qualified_stats(self, start, end):
        """
        Return a player_set queryset filtered by year and number of players
        that have participated in the related games.

        Args:
            start, end - start and end dates
        """
        return self.player_set.filter(
            # limit the queryset to the specified period
            models.Q(
                game__date_finished__gte=start, 
                game__date_finished__lte=end
            ),
            # limit the queryset with the min number of players played in a game
            models.Q(game__player_num__gte=Profile.MIN_PLAYERS) | 
                # unless its a COOP game
                models.Q(game__gametype__in=definitions.MODES_COOP)
        )

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
        for pattern in const.POPULAR_NAMES:
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
        """
        Insert or update a Rank entry specific to given board number and ranking period.

        Return a tuple containing the affected entry and a boolean indicating whether the entry was created.

        Args:
            category - category id
            year - year number
            profile - profile that has to be ranked
            points - number of points
        """
        if points <= 0:
            return (None, False)
        try:
             # aquire a row lock
            entry = (self.get_queryset()
                .select_for_update()
                .get(category=category, year=year, profile=profile)
            )
        except ObjectDoesNotExist:
            return (self.get_queryset().create(
                category=category, year=year, profile=profile, points=points
            ), True)
        else:
            if entry.points != points:
                entry.points = points
                entry.save(update_fields=['points'])
        return (entry, False)

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
    category = models.SmallIntegerField(choices=[(int(getattr(Profile, attr)), attr) for attr in vars(Profile) if attr.startswith('STATS_')])
    year = models.SmallIntegerField()
    profile = models.ForeignKey('Profile')
    points = models.FloatField(default=0)
    position = models.PositiveIntegerField(null=True)
    objects = RankManager()

    class Meta:
        index_together = (('year', 'category'),)
        unique_together = (('year', 'profile', 'category'),)

    def __str__(self):
        return '{0.period}:{0.category} {0.profile} ({0.points})'.format(self)

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