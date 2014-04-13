# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import datetime
import random
import logging
from functools import reduce
import six

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.views import generic
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext_lazy, pgettext, ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django import db
from django.utils.encoding import force_text
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db.models import Q
import aggregate_if
import cacheops
from julia import shortcuts

from .decorators import (requires_valid_request, requires_valid_source, requires_unique_request)
from .signals import stream_data_received
from . import models, forms, definitions, utils, const

logger = logging.getLogger(__name__)


class AnnualViewMixin(object):
    MIN_YEAR_DAYS = 14
    # list of available years
    years = None
    # selected year
    year = None
    # current year
    year_now = None

    @property
    def year_min(self):
        return self.years[0]

    @property
    def year_max(self):
        return self.years[-1]

    def __init__(self, *args, **kwargs):
        self.year_now = timezone.now().year
        # get a range of all available years starting from the earliest one
        self.years = list(range(self.get_min_year() or self.year_now, self.year_now + 1))
        super(AnnualViewMixin, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        if not kwargs.get('year', None):
            # skip the current year if its too early.. 
            if (timezone.now() - models.Rank.get_period_for_year(self.year_max)[0]).days < self.MIN_YEAR_DAYS and len(self.years) > 1:
                #..unless its the only year
                self.year = self.years[-2]
            else:
                self.year = self.years[-1]
        else:
            self.year = int(kwargs['year'])
        # raise 404 if the year is not in the list
        if self.year not in self.years:
            raise Http404
        return super(AnnualViewMixin, self).get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context_data = super(AnnualViewMixin, self).get_context_data(*args, **kwargs)
        context_data.update({
            # get the 2 close years for navigation
            'years': list(reversed([year for year in self.years if abs(self.year - year) <= 1])),
            'year': self.year,
            'years_extreme': {
                'min': self.year_min,
                'max': self.year_max,
            },
            'year_now': self.year_now,
            'year_previous': (self.year - 1) if self.year > self.year_min else None,
            'year_next': (self.year + 1) if self.year < self.year_max else None,
        })
        return context_data

    def get_min_year(self):
        @cacheops.cached(timeout=60*60*24)
        def _get_min_year():
            return models.Rank.objects.aggregate(year=db.models.Min('year'))['year']
        return _get_min_year()


class StreamView(generic.View):

    STATUS_OK = '0'
    STATUS_ERROR = '1'

    @staticmethod
    def status(request, code, message=None):
        """
        Return an integer status code followed by an optional message.
        The status and message are delimited with a new line

        Examples:
            1. 0
            2. 0\nData has been accepted
            3. 1\nOutdated mod version. Please update to 1.2.3
            3. 1\nInvalid server key
            4. 1\nThe server is not registered
        """
        return HttpResponse('\n'.join(list(filter(None, [code, message]))))

    @method_decorator(requires_valid_request(definitions.stream_pattern_node))
    @method_decorator(requires_unique_request)
    @method_decorator(requires_valid_source)
    def post(self, request):
        """
        """
        logger.debug('receieved stream data from {}:{}'
            .format(request.stream_source.ip, request.stream_source.port)
        )
        stream_data_received.send(
            self, data=request.stream_data, server=request.stream_source
        )
        return StreamView.status(request, StreamView.STATUS_OK)

    def get(self, request):
        """
        Display data streaming tutorial.
        """
        return render(request, 'stream.html', {})

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(StreamView, self).dispatch(*args, **kwargs)


class MainView(generic.TemplateView):
    template_name = 'tracker/main.html'

    def get_context_data(self, **kwargs):
        context_data = super(MainView, self).get_context_data(**kwargs)
        context_data.update({
            #'featured_players': self.get_featured_players(),
            'featured_games': self.get_featured_games(),
        })
        return context_data

    def get_featured_games(self):
        offset = random.randint(0, 50)
        featured_games = list((models.Game.objects
            .extra(select={'score_total': 'score_swat + score_sus'}, order_by=('-score_total',))[offset:offset+18]
        ))
        random.shuffle(featured_games)
        return featured_games

    def get_featured_players(self):
        return (models.Rank.objects
            .filter(category=const.STATS_SCORE)
            .order_by('-points')[:10]
        )


class TopListView(AnnualViewMixin, generic.ListView):
    template_name = 'tracker/top_list.html'
    model = models.Rank

    boards = (
        ('score', _('Top Score'), const.STATS_SCORE),
        ('time', _('Time Played'), const.STATS_TIME),
        #('kills', _('Kills'), const.STATS_KILLS),
        ('spm', _('Score/Minute'), const.STATS_SPM),
        ('coop_score', _('COOP Score'), const.STATS_COOP_SCORE),
    )

    limit = 5

    def get_queryset(self, *args, **kwargs):
        return (super(TopListView, self).get_queryset(*args, **kwargs)
            .select_related('profile')
            .filter(year=self.year)
            .order_by('-points')
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super(TopListView, self).get_context_data(*args, **kwargs)
        context_data.update(self.get_objects())
        return context_data

    def get_objects(self):
        boards = []
        for context_name, board_name, category in self.boards:
            boards.append(
                (context_name, board_name, self.get_queryset().filter(category=category)[:self.limit])
            )
        return {'boards': boards}


class BoardListView(TopListView):
    template_name = 'tracker/board_list.html'
    paginate_by = 50

    boards = (
        [_('Score'), (
            ('score', _('Score'), const.STATS_SCORE, 'int'),
            ('top_score', _('Highest Score'), const.STATS_TOP_SCORE, 'int'),
            ('time', _('Time Played'), const.STATS_TIME, 'time'),
            ('games', _('Rounds Played'), const.STATS_GAMES, 'int'),
            ('wins', _('Wins'), const.STATS_WINS, 'int'),
            ('spm', _('Score/Minute'), const.STATS_SPM, 'float'),
            ('spr', _('Score/Round'), const.STATS_SPR, 'float'),
        )],
        [_('Kills'), (
            ('kills', _('Kills'), const.STATS_KILLS, 'int'),
            ('kdr', _('K/D Ratio'), const.STATS_KDR, 'float'),
            ('arrests', _('Arrests'), const.STATS_ARRESTS, 'int'),
            ('kill_streak', _('Highest Kill Streak'), const.STATS_KILL_STREAK, 'int'),
            ('arrest_streak', _('Highest Arrest Streak'), const.STATS_ARREST_STREAK, 'int'),
        )],
        [_('MODE_1'), (
            #('vip_times', _('Times Played the VIP'), const.STATS_VIP_TIMES, 'int'),
            ('vip_escapes', _('VIP Escapes'), const.STATS_VIP_ESCAPES, 'int'),
            ('vip_captures', _('VIP Captures'), const.STATS_VIP_CAPTURES, 'int'),
            ('vip_rescues', _('VIP Rescues'), const.STATS_VIP_RESCUES, 'int'),
            ('vip_kills_valid', _('VIP Kills'), const.STATS_VIP_KILLS_VALID, 'int'),
        )],
        [_('MODE_2'), (
            ('rd_bombs_defused', _('Bombs Disarmed'), const.STATS_RD_BOMBS_DEFUSED, 'int'),
        )],
        [_('MODE_4'), (
            ('sg_escapes', _('Case Escapes'), const.STATS_SG_ESCAPES, 'int'),
            ('sg_kills', _('Case Carrier Kills'), const.STATS_SG_KILLS, 'int'),
        )],
        [_('MODE_3'), (
            ('coop_score', _('Score'), const.STATS_COOP_SCORE, 'int'),
            ('coop_time', _('Time Played'), const.STATS_COOP_TIME, 'time'),
            ('coop_games', _('Missions Attempted'), const.STATS_COOP_GAMES, 'int'),
            ('coop_wins', _('Missions Completed'), const.STATS_COOP_WINS, 'int'),
            ('coop_enemy_arrests', _('Suspects Arrested'), const.STATS_COOP_ENEMY_ARRESTS, 'int'),
            ('coop_enemy_kills', _('Suspects Killed'), const.STATS_COOP_ENEMY_KILLS, 'int'),
            ('coop_hostage_arrests', _('Civilians Arrested'), const.STATS_COOP_HOSTAGE_ARRESTS, 'int'),
            #('coop_toc_reports', _('Characters Reported to TOC'), const.STATS_COOP_TOC_REPORTS, 'int'),
        )],
    )
    board_name_default = 'score'

    def get(self, *args, **kwargs):
        "Set the active leaderboard."
        board_name = self.kwargs.get('board_name', None)
        # check the request board name
        if board_name:
            if board_name not in [board[0] for board in self.get_boards()]:
                raise Http404
        else:
            board_name = self.board_name_default
        # get the board details
        self.board = dict((board[0], board) for board in self.get_boards())[board_name]
        return super(BoardListView, self).get(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return (super(BoardListView, self).get_queryset(*args, **kwargs)
            .filter(category=self.board[2])
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super(BoardListView, self).get_context_data(*args, **kwargs)
        filters = self.request.GET.copy()
        if 'page' in filters:
            del filters['page']
        context_data.update({
            'filters': filters,
            'boards': self.boards,
            'board': self.board,
        })
        return context_data

    def get_boards(self):
        for category, boards in self.boards:
            for board in boards:
                yield board

    def get_objects(self):
        return {}


class GameOnlineListView(generic.ListView):
    template_name = 'tracker/chapters/game/game_list.html'
    model = models.Game


class GameListView(generic.ListView):
    template_name = 'tracker/chapters/game/game_list.html'
    #context_object_name = 'game_list'
    model = models.Game
    paginate_by = 50
    form_class = forms.GameFilterForm
    form = None
    initial = {}

    def get(self, request, *args, **kwargs):
        self.form = self.form_class(data=request.GET, initial=self.initial.copy())
        return super(GameListView, self).get(request, *args, **kwargs) 

    def get_context_data(self, *args, **kwargs):
        context_data = super(GameListView, self).get_context_data(*args, **kwargs)
        filters = self.request.GET.copy()
        if 'page' in filters:
            del filters['page']
        context_data.update({
            'form': self.form,
            'filters': filters,
        })
        return context_data

    def get_queryset(self, *args, **kwargs):
        qs = (super(GameListView, self).get_queryset(*args, **kwargs))
        # only do further lookup if the form is valid
        if not self.form.is_valid():
            return qs.none()
        # filter by map
        if self.form.cleaned_data.get('map', None):
            qs = qs.filter(mapname=self.form.cleaned_data['map'])
        # filter by gametime
        if self.form.cleaned_data.get('gametime', None):
            qs = qs.filter(time__gte=self.form.cleaned_data['gametime']*60)
        # filter by outcome
        if self.form.cleaned_data.get('outcome', None):
            qs = qs.filter(outcome=self.form.cleaned_data['outcome'])
        # filter by gametype
        if self.form.cleaned_data.get('gametype', None):
            qs = qs.filter(gametype=self.form.cleaned_data['gametype'])
        # filter by server
        if self.form.cleaned_data.get('server', None):
            qs = qs.filter(server=self.form.cleaned_data['server'])
        # filter by participated players
        if self.form.cleaned_data.get('players', None):
            for name in self.form.cleaned_data['players']:
                qs = qs.filter(player__alias__name__icontains=name)
        return qs.order_by('-date_finished').distinct()


class GameDetailView(generic.DetailView):
    TEMPLATE_DEFAULT = 'tracker/chapters/game/game_detail.html'
    TEMPLATE_MODE = 'tracker/chapters/game/game_mode%(mode)s_detail.html'

    pk_url_kwarg = 'game_id'
    model = models.Game

    # "Highest" categories
    categories = {
        'all': (
            ('score', _('Highest Score'), ngettext_lazy('%d point', '%d points')),
            ('kills', _('Most Kills'), ngettext_lazy('%d kill', '%d kills')),
            ('accuracy', _('Highest Accuracy'), _('%d%%')),
            ('kill_streak', _('Highest Kill Streak'), ngettext_lazy('%d kill', '%d kills')),
        ),
        definitions.MODE_VIP: (),
    }

    def get_template_names(self, *args, **kwargs):
        return [self.TEMPLATE_MODE % {'mode': self.object.gametype}, self.TEMPLATE_DEFAULT]

    def get_context_data(self, *args, **kwargs):
        players = models.Player.objects.prefetched().filter(game=self.object.pk)
        # sort by score, kills, arrests, -deaths
        key = lambda player: (player.score, player.kills, player.arrests, -player.deaths)
        players = sorted(players, key=key, reverse=True)
        # pick players that finished the game
        players_online = [player for player in players if not player.dropped]
        # pick the ones that have dropped
        players_dropped = [player for player in players if player.dropped]

        context_data = super(GameDetailView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'players': players,
            'players_online': players_online,
            'players_dropped': players_dropped,
            'players_blue': [player for player in players_online if player.team == definitions.TEAM_BLUE],
            'players_red': [player for player in players_online if player.team == definitions.TEAM_RED],

            'players_highest': self.get_featured_players(players),
            'player_best': self.get_best_player(players),

            'games_close': self.get_close_games(),
        })
        # coop specific details
        if self.object.coop_game:
            procedures = self.object.procedure_set.all()
            procedures_bonus = list(filter(
                lambda procedure: procedure.name_translated.startswith('bonus'), 
                procedures
            ))
            procedures_penalty = list(filter(
                lambda procedure: procedure.name_translated.startswith('penalty') and procedure.score, 
                procedures
            ))
            score_bonus = utils.calc_coop_score(procedures_bonus)
            score_penalty = utils.calc_coop_score(procedures_penalty)

            context_data.update({
                'objectives': self.object.objective_set.all(),
                'procedures': {
                    'bonus': {'list': procedures_bonus, 'score': score_bonus},
                    'penalty': {'list': procedures_penalty, 'score': score_penalty},
                },
                # normal: 0-100
                'coop_rank': self.get_coop_rank(self.object.coop_score_normal),
            })
        return context_data

    def get_queryset(self, *args, **kwargs):
        return (super(GameDetailView, self).get_queryset(*args, **kwargs)
            .select_related('server', 'server__serverstatus')
        )

    def get_close_games(self):
        "Return the games preceding and following this one."

        qs = models.Game.objects.filter(server=self.object.server)
        previous = qs.filter(pk__lt=self.object.pk).order_by('-pk')
        next = qs.filter(pk__gt=self.object.pk).order_by('pk')

        return {
            'previous': previous.first(),
            'next': next.first(),
        }

    def get_featured_players(self, players):
        categories = []
        featured = []
        # append mode specific stats
        if self.object.gametype in self.categories:
            categories.extend(self.categories[self.object.gametype])
        # append common stats
        categories.extend(self.categories['all'])

        for category, category_translated, points_translated in categories:
            sortable = sorted(players, key=utils.sort_key(category), reverse=True)
            player = next(iter(sortable), None)
            if player:
                points = getattr(player, category)
                featured.append({
                    'category': category,
                    'category_translated': category_translated, 
                    'player': player,
                    'points': points,
                    'points_translated': points_translated % points,
                })
        return featured

    def get_best_player(self, players):
        """
        Return the player of the game.

        Args:
            players - list of participated players
        """
        swat = [player for player in players if player.team == definitions.TEAM_BLUE]
        suspects = [player for player in players if player.team == definitions.TEAM_RED]
        # use the following attrs as a fallback
        comparable = ['score', 'kills', 'arrests', '-deaths', '-arrested']
        sortable = players
        # there is no best player in COOP ;-)
        if self.object.gametype in definitions.MODES_COOP:
            return None
        if self.object.gametype == definitions.MODE_VIP:
            if self.object.outcome in definitions.SWAT_GAMES:
                sortable = swat
                comparable = ['-vip_kills_invalid', 'vip_rescues', 'vip_escapes'] + comparable
            elif self.object.outcome in definitions.SUS_GAMES:
                sortable = suspects
                comparable = ['-vip_kills_invalid', 'vip_captures', 'vip_kills_valid'] + comparable
        else:
            raise NotImplementedError
        sortable = sorted(sortable, key=utils.sort_key(*comparable), reverse=True)
        return next(iter(sortable), None)

    @staticmethod
    def get_coop_rank(score):
        if score >= 100:
            return _('Chief Inspector')
        elif score >= 95:
            return _('Inspector')
        elif score >= 90:
            return _('Captain')
        elif score >= 85:
            return _('Lieutenant')
        elif score >= 80:
            return _('Sergeant')
        elif score >= 75:
            return _('Patrol Officer')
        elif score >= 70:
            return _('Reserve Officer')
        elif score >= 60:
            return _('Non-sworn Officer')
        elif score >= 50:
            return _('Recruit')
        elif score >= 35:
            return _('Washout')
        elif score >= 20:
            return _('Vigilante')
        elif score >= 0:
            return _('Menace')
        return _('Cheater')


class ServerListView(generic.ListView):
    template_name = 'tracker/chapters/server/server_list.html'
    queryset = models.ServerStatus.objects.online()

    def get_queryset(self, *args, **kwargs):
        return super(ServerListView, self).get_queryset(*args, **kwargs).order_by('-player_num')


class ServerDetailView(generic.DetailView):
    model = models.Server
    template_name = 'tracker/chapters/server/server_detail.html'

    class ServerNotAvailable(Exception):
        pass

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super(ServerDetailView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            response = super(ServerDetailView, self).get(request, *args, **kwargs)
        except self.ServerNotAvailable:
            return render(request, 'tracker/chapters/server/server_cap.html', {})
        else:
            return response

    def get_object(self, *args, **kwargs):
        ip = self.kwargs.get('server_ip', None)
        port = self.kwargs.get('server_port', None)

        if not (ip and port):
            raise AttributeError

        try:
            obj = self.get_queryset().get(ip=ip, port=port)
        except ObjectDoesNotExist:
            raise Http404('No server found matching ip=%(ip)s, port=%(port)s' % {'ip': ip, 'port': port})

        if not obj.enabled:
            raise self.ServerNotAvailable

        return obj

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServerDetailView, self).get_context_data(*args, **kwargs)

        status = self.object.status.query_status()
        if not status:
            raise self.ServerNotAvailable

        players = [player for key, player in sorted(status['players'].items())] if 'players' in status else []

        context_data.update({
            'game': status,
            'players': players,
            'players_blue': [player for player in players if int(player['team']) == definitions.TEAM_BLUE],
            'players_red': [player for player in players if int(player['team']) == definitions.TEAM_RED],
        })
        return context_data


class ProfileBaseView(AnnualViewMixin, generic.DetailView):
    GAMES_RECENT_MAX = 50
    MAPS_RECENT_MAX = 10

    class ProfileNotPrepared(Exception): 
        pass

    model = models.Profile
    pk_url_kwarg = 'profile_id'

    view = None

    def get(self, request, *args, **kwargs):
        try:
            response = super(ProfileBaseView, self).get(request, *args, **kwargs)
        except self.ProfileNotPrepared:
            return render(request, 'tracker/chapters/profile/profile_cap.html', {})
        else:
            # redirect to the latest avaiable profile.. unless its specified
            if not kwargs.get('year') and self.object.date_played.year != self.year_now:
                return HttpResponseRedirect(
                    utils.get_profile_url(self.object, self.view, **{'year': self.object.date_played.year})
                )
            return response

    def get_object(self, *args, **kwargs):
        obj = super(ProfileBaseView, self).get_object(*args, **kwargs)
        if not obj.popular:
            raise self.ProfileNotPrepared
        return obj

    def get_context_data(self, *args, **kwargs):
        games = self.get_extreme_dates()
        # limit the years list with the range of years the player played in
        self.years = list(range(games['first_seen'].date_finished.year, games['last_seen'].date_finished.year + 1))
        context_data = super(ProfileBaseView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'recent': self.get_recent_games(),
            'view': self.view,
        })
        return context_data

    def get_games(self):
        return (models.Game.objects.filter(player__profile=self.object).order_by('-pk'))

    def get_stats(self):
        stored = {}
        # turn the id => name tuple into a dict
        d = dict(definitions.STATS)
        for score in self.object.rank_set.filter(year=self.year):
            stored[score.category] = score.points
        return {value: stored[key] if key in stored else 0.0 for key, value in six.iteritems(d)}

    def get_recent_games(self):
        @cacheops.cached_as(models.Game, extra=self.object.pk)
        def _get_recent_games():
            recent = []
            map_count = 0
            map_name = None
            games = self.get_games()[:self.GAMES_RECENT_MAX]
            # attempt to limit the number of displayed games by the number of maps
            for game in games:
                if game.mapname != map_name:
                    map_name = game.mapname
                    map_count += 1
                if map_count >= self.MAPS_RECENT_MAX:
                    break
                recent.append(game)
            return recent
        return _get_recent_games()

    def get_weapons(self):
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _get_weapons():
            aggregated = self.object.aggregate_weapon_stats(
                *models.Rank.get_period_for_year(self.year), 
                filters={'game__gametype__in': definitions.MODES_VERSUS}
            )
            return aggregated
        return _get_weapons()

    def get_extreme_dates(self):
        @cacheops.cached(timeout=60*60, extra=self.object.pk)
        def _get_extreme_dates():
            qs = models.Game.objects.filter(player__profile=self.object)
            return {
                'first_seen': qs.order_by('date_finished')[:1].get(),
                'last_seen': qs.order_by('-date_finished')[:1].get(),
            }
        return _get_extreme_dates()

    def get_weapon_stats(self, aggregated):
        """
        Return overall weapon related stats (e.g. total number of shots fired)
        """
        ammo_weapons = {
            weapon: stats for (weapon, stats) in six.iteritems(aggregated)
            if weapon in definitions.WEAPONS_FIRED
        }
        ammo_hits = 0
        ammo_fired = 0
        for weapon, stats in six.iteritems(ammo_weapons):
            ammo_fired += stats['shots']
            ammo_hits += stats['hits']
        stats = {
            'kill_distance': reduce(
                lambda x, y: x if x > y['distance'] else y['distance'], six.itervalues(aggregated), 0.0
            ),
            'ammo_accuracy': utils.calc_ratio(ammo_hits, ammo_fired, min_divisor=models.Profile.MIN_AMMO),
            'ammo_fired': ammo_fired,
            'ammo_hits': ammo_hits,
            'ammo_teamhits': reduce(lambda x, y: x + y['teamhits'], six.itervalues(ammo_weapons), 0),
            'ammo_teamkills': reduce(lambda x, y: x + y['teamkills'], six.itervalues(ammo_weapons), 0),
        }
        return stats


class ProfileDetailView(ProfileBaseView):
    template_name = 'tracker/chapters/profile/profile_overview_detail.html'

    view = 'tracker:profile_detail'

    def get_context_data(self, *args, **kwargs):
        stats = self.get_stats()
        map_stats = self.get_map_stats()
        weapons = self.get_weapons()

        context_data = super(ProfileDetailView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'weapons': weapons,
            'stats': dict(stats, **self.get_weapon_stats(weapons)),
            'ratio_max': self.get_max_ratio(),
            'best': {
                'score': self.get_best_game(stats.get('top_score', 0)),
                'weapon': self.get_best_weapon(weapons),
            },
            'maps': map_stats,
            'maps_best': utils.rank_dicts(map_stats),
            'extreme': self.get_extreme_dates(),
            #'all_stats': self.object.aggregate_mode_stats(models.Profile.SET_STATS_ALL, *models.Rank.get_period_for_year(self.year)),
        })
        return context_data

    def get_map_stats(self):
        items = {
            'time': (
                aggregate_if.Sum(
                    'score__points', 
                    Q(
                        score__category=const.STATS_TIME,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            'games': (
                aggregate_if.Count(
                    'game', 
                    only=Q(game__gametype__in=definitions.MODES_VERSUS),
                    distinct=True
                )
            ),
            'score': (
                aggregate_if.Sum(
                    'score__points', 
                    Q(
                        score__category=const.STATS_SCORE,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            'top_score': (
                aggregate_if.Max(
                    'score__points', 
                    Q(
                        score__category=const.STATS_SCORE,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            'kills': (
                aggregate_if.Max(
                    'score__points', 
                    Q(
                        score__category=const.STATS_KILLS,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            'deaths': (
                aggregate_if.Max(
                    'score__points', 
                    Q(
                        score__category=const.STATS_DEATHS,
                        game__gametype__in=definitions.MODES_VERSUS
                    )
                )
            ),
            'wins': (
                aggregate_if.Count(
                    'game', 
                    only=(Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SWAT_GAMES) |
                        Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SUS_GAMES)),
                    distinct=True
                )
            ),
            'losses': (
                aggregate_if.Count(
                    'game', 
                    only=(Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SUS_GAMES) |
                        Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SWAT_GAMES)),
                    distinct=True
                )
            ),
        }

        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _get_map_stats():
            aggregated = self.object.aggregate(items, *models.Rank.get_period_for_year(self.year), group_by='game__mapname')
            return [item for item in aggregated if item['games']]
        return _get_map_stats()

    def get_best_game(self, points):
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _get_best_game():
            try:
                return (self.object._qualified_stats(*models.Rank.get_period_for_year(self.year))
                    .select_related('game')
                    .prefetch_related('score_set')
                    .filter(score__category=const.STATS_SCORE, score__points=points)[:1]
                    .get()
                )
            except ObjectDoesNotExist:
                return None
        return _get_best_game()

    def get_best_weapon(self, aggregated):
        "Return the kills weapons."
        return next(iter(sorted(six.itervalues(aggregated), key=lambda weapon: weapon['kills'], reverse=True)), None)

    def get_max_ratio(self, *categories):
        "Return the max values for the K/D and S/M stats."
        @cacheops.cached(timeout=60*60*24)
        def _get_max_ratio():
            return (models.Rank.objects
                .filter(year=self.year)
                .aggregate(
                    spm=aggregate_if.Max('points', only=Q(category=const.STATS_SPM)),
                    kdr=aggregate_if.Max('points', only=Q(category=const.STATS_KDR))
                )
            )
        return _get_max_ratio()


class ProfileWeaponListView(ProfileBaseView):
    PRIMARY = definitions.unmap(
        definitions.stream_pattern_node.item('players').item, 'loadout__primary', (
            'M4 Super90',
            'Nova Pump',
            'Pepper-ball',
            'Less Lethal Shotgun',
            'Colt M4A1 Carbine',
            'AK-47 Machinegun',
            'GB36s Assault Rifle',
            'Gal Sub-machinegun',
            '9mm SMG',
            'Suppressed 9mm SMG',
            '.45 SMG',
            'Colt Accurized Rifle',
            '40mm Grenade Launcher',
            '5.56mm Light Machine Gun',
            '5.7x28mm Submachine Gun',
            '9mm Machine Pistol',
        )
    )
    SECONDARY = definitions.unmap(
        definitions.stream_pattern_node.item('players').item, 'loadout__primary', (
            'M1911 Handgun',
            '9mm Handgun',
            'Colt Python',
            'VIP Colt M1911 Handgun',
            'Mark 19 Semi-Automatic Pistol',
            'Cobra Stun Gun',
        )
    )
    TACTICAL = definitions.unmap(
        definitions.stream_pattern_node.item('players').item, 'loadout__primary', (
            'Taser Stun Gun',
            'Cobra Stun Gun',
            'Pepper Spray',
            'Stinger',
            #'CS Gas',
            'Flashbang',
            'Shotgun',
            'Zip-cuffs',
            'Optiwand',
        )
    )

    template_name = 'tracker/chapters/profile/profile_weapon_list.html'

    view = 'tracker:profile_equipment_list'

    def get_context_data(self, *args, **kwargs):
        weapons = {
            weapon: stats for weapon, stats in six.iteritems(self.get_weapons()) if stats['kills'] or stats['shots']
        }
        # sort primary and secondary weapons by kills
        weapons_fired = sorted(
            self.filter_weapons(self.PRIMARY + self.SECONDARY, weapons).values(), 
            key=lambda weapon: weapon['kills'],
            reverse=True
        )
        # sort tactical weapons by number of shots
        weapons_tactical = sorted(
            self.filter_weapons(self.TACTICAL, weapons).values(),
            key=lambda weapon: weapon['shots'],
            reverse=True
        )
        context_data = super(ProfileWeaponListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'weapons': weapons_fired,
            'weapons_best': utils.rank_dicts(weapons_fired),
            'tactical': weapons_tactical, 
            'tactical_best': utils.rank_dicts(weapons_tactical),
            'loadout': self.object.loadout,
        })
        return context_data

    @staticmethod
    def filter_weapons(pattern, weapons):
        filtered = {}
        for weapon in weapons:
            # check whether the weapon code is in the unmapped pattern tuple
            if int(weapon) in pattern:
                filtered[weapon] = weapons[weapon]
        return filtered


class ProfileCoopDetailView(ProfileBaseView):
    template_name = 'tracker/chapters/profile/profile_coop_detail.html'

    view = 'tracker:profile_coop_detail'

    def get_context_data(self, *args, **kwargs):
        context_data = super(ProfileCoopDetailView, self).get_context_data(*args, **kwargs)

        maps = self.get_map_stats()
        equipment = self.get_favourite_equipment()
        # annotate with fav equipment
        for item in maps:
            item['loadout'] = equipment[item['mapname']] if item['mapname'] in equipment else None

        context_data.update({
            'stats': dict(self.get_stats(), **self.get_weapon_stats(self.get_weapons())),
            'maps': maps,
        })
        return context_data

    def get_map_stats(self):
        items = {
            'score_best': (
                db.models.Max('game__coop_score')
            ),
            'score_avg': (
                db.models.Avg('game__coop_score')
            ),
            'time_avg': (
                aggregate_if.Min(
                    'game__time', 
                    only=Q(game__outcome__in=definitions.COMPLETED_MISSIONS)
                )
            ),
            'time_best': (
                aggregate_if.Min(
                    'game__time', 
                    only=Q(game__outcome__in=definitions.COMPLETED_MISSIONS)
                )
            ),
            'objectives_completed': (
                aggregate_if.Count(
                    'game__objective', 
                    only=Q(game__objective__status=definitions.OBJECTIVE_COMPLETED),
                    distinct=True
                )
            ),
            'objectives_failed': (
                aggregate_if.Count(
                    'game__objective', 
                    only=Q(game__objective__status=definitions.OBJECTIVE_FAILED),
                    distinct=True
                )
            ),
            'missions_completed': (
                aggregate_if.Count(
                    'game', 
                    only=Q( game__outcome__in=definitions.COMPLETED_MISSIONS),
                    distinct=True
                )
            ),
            'missions_failed': (
                aggregate_if.Count('game', 
                    only=Q(game__outcome__in=definitions.FAILED_MISSIONS),
                    distinct=True
                )
            ),
        }
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _coop_get_map_stats():
            aggregated = self.object.aggregate(
                items, 
                *models.Rank.get_period_for_year(self.year), 
                group_by='game__mapname',
                filters={'game__gametype__in': definitions.MODES_COOP, 'dropped': False}
            )
            return [item for item in aggregated if item['time_best']]
        return _coop_get_map_stats()

    def get_favourite_equipment(self):
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _coop_get_favourite_equipment():
            maps = {}
            aggregated = (self.object
                ._qualified_stats(*models.Rank.get_period_for_year(self.year))
                .filter(game__gametype__in=definitions.MODES_COOP)
                .values('game__mapname', 'loadout')
                .annotate(count=db.models.Count('loadout')).order_by('-count')
            )
            for item in aggregated:
                # filter out None entries
                if item['game__mapname'] is None or item['loadout'] is None:
                    continue
                # since the aggregate query is ordered by loadout count, 
                # we get the most popular loadout for every first occurence of a map
                if item['game__mapname'] not in maps:
                    maps[item['game__mapname']] = item['loadout']
            # prefetch Loadout objects
            # construct a pk => Loadout object dict from the queryset
            prefetched = {
                obj.pk: obj for obj in models.Loadout.objects.filter(pk__in=maps.values())
            }
            return {
                mapname: prefetched[pk] for mapname, pk in six.iteritems(maps)
            }
        return _coop_get_favourite_equipment()

    def get_weapons(self):
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _coop_get_weapons():
            return self.object.aggregate_weapon_stats(
                *models.Rank.get_period_for_year(self.year), 
                filters={'game__gametype__in': definitions.MODES_COOP}
            )
        return _coop_get_weapons()


class ProfileHistoryListView(ProfileBaseView, generic.list.MultipleObjectMixin):
    template_name = 'tracker/chapters/profile/profile_history_list.html'
    paginate_by = 50
    object_list = None

    view = 'tracker:profile_history_list'

    def get_context_data(self, *args, **kwargs):
        start, end = models.Rank.get_period_for_year(self.year)
        # for paginator
        self.object_list = (self.get_games()
            .filter(date_finished__gte=start, date_finished__lte=end)
        )
        context_data = super(ProfileHistoryListView, self).get_context_data(*args, **kwargs)
        return context_data