# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import datetime
import random
import logging
import collections
from functools import reduce

import six
from dateutil import relativedelta

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.views import generic
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext_lazy, pgettext, ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django import db
from django.utils.encoding import force_text
from django.utils import timezone, timesince
from django.contrib.humanize.templatetags import humanize
from django.views.decorators.cache import never_cache
from django.db.models import Q
import aggregate_if
import cacheops
from julia import shortcuts

from .decorators import (requires_valid_request, requires_valid_source, requires_unique_request)
from .signals import stream_data_received
from . import models, forms, definitions, utils, const, templatetags

logger = logging.getLogger(__name__)


class AnnualViewMixin(object):
    # min days since jan 01 the new year will not considered interesting (since lack of data)
    MIN_YEAR_DAYS = 7
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
            raise Http404(_('%(year)s is not a valid year.') % {'year': self.year })
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

    @classmethod
    def get_min_year(cls):
        # cache untill tomorrow
        @cacheops.cached(timeout=(utils.tomorrow()-timezone.now()).seconds)
        def _get_min_year():
            return models.Rank.objects.aggregate(year=db.models.Min('year'))['year']
        return _get_min_year()


class FilterViewMixin(object):

    def get_context_data(self, *args, **kwargs):
        filters = self.request.GET.copy()

        if 'page' in filters:
            del filters['page']

        context_data = super(FilterViewMixin, self).get_context_data(*args, **kwargs)
        context_data.update({
            'filters': filters,
        })
        return context_data


class SummaryViewMixin(object):

    def get_context_data(self, *args, **kwargs):
        context_data = super(SummaryViewMixin, self).get_context_data(*args, **kwargs)
        context_data.update({
            'summary': self.get_summary(),
        })
        return context_data

    def get_summary(self):
        raise NotImplementedError

    @classmethod
    def get_period(cls):
        now = timezone.now()
        today = utils.today()
        weekday = now.isoweekday()
        # get the curent month's date
        month = datetime.datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # get the current week's date
        week = today-datetime.timedelta(days=weekday-1)
        # display current month summary
        if now.day >= 25:
            return (_('Monthly Summary'), month, now)
        # display past month summary
        elif now.day <= 1:
            return (_('Monthly Summary'), month-relativedelta(months=1), now)
        # display current week summary
        elif weekday >= 4:
            return (_('Weekly Summary'), week, now)
        # display past week summary
        elif weekday <= 1:
            return (_('Weekly Summary'), week-datetime.timedelta(days=7), now)
        else:
            return None


class FeaturedViewMixin(object):
    sample = 500
    limit = 10

    def get_context_data(self, *args, **kwargs):
        context_data = super(FeaturedViewMixin, self).get_context_data(*args, **kwargs)
        context_data.update({
            'featured': self.get_featured_games(),
        })
        return context_data

    def get_featured_games(self):
        qs = (models.Game.objects
            .extra(
                select={'score_total': 'score_swat + score_sus'}, 
                order_by=('-score_total',)
            )
        )
        # get random offset
        offset = random.randint(0, self.sample)
        return qs[offset:offset+self.limit]


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
    @method_decorator(requires_valid_source)
    def post(self, request):
        logger.debug('receieved stream data from {}:{}'
            .format(request.stream_source.ip, request.stream_source.port)
        )
        stream_data_received.send(sender=None, data=request.stream_data, server=request.stream_source)
        return StreamView.status(request, StreamView.STATUS_OK)

    def get(self, request):
        """Display data streaming tutorial."""
        return render(request, 'tracker/chapters/stream/stream.html', {})

    @method_decorator(never_cache)
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(StreamView, self).dispatch(*args, **kwargs)


class MainView(SummaryViewMixin, FeaturedViewMixin, generic.TemplateView):
    template_name = 'tracker/chapters/main/main.html'

    summary = (
        (
            _('Highest Score'), 
            db.models.Sum('score'), 
            lambda value: ngettext_lazy('%d points', '%d points') % value
        ),
        (
            _('Highest Playtime'), 
            aggregate_if.Sum('time', only=Q(game__gametype__in=definitions.MODES_VERSUS)), 
            lambda value: templatetags.humantime(value)
        ),
        (
            _('Best Round Score'), 
            db.models.Max('score'), 
            lambda value: ngettext_lazy('%d point', '%d points') % value
        ),
        (
            _('Most Kills'), 
            db.models.Sum('kills'), 
            lambda value: ngettext_lazy('%d kill', '%d kills') % value
        ),
        (
            _('Most Arrests'), 
            db.models.Sum('arrests'), 
            lambda value: ngettext_lazy('%d arrest', '%d arrests') % value
        ),
        (
            _('Highest Kill Streak'), 
            db.models.Max('kill_streak'), 
            lambda value: ngettext_lazy('%d kill', '%d kills') % value
        ),
        # (
        #     _('Highest CO-OP Score'), 
        #     db.models.Sum('game__coop_score'), 
        #     lambda value: ngettext_lazy('%d points', '%d points') % value
        # ),
        # (
        #     _('Highest CO-OP Playtime'), 
        #     aggregate_if.Sum('time', only=Q(game__gametype__in=definitions.MODES_COOP)), 
        #     lambda value: templatetags.humantime(value)
        # ),
    )

    def get_summary(self):
        now = timezone.now()
        # cache untill tomorrow
        @cacheops.cached(timeout=(utils.tomorrow()-timezone.now()).seconds)
        def _get_summary():
            summary = []
            period = self.get_period()

            if not period:
                return None

            period_title, start, end = period

            for title, agg_obj, translate in self.summary:
                try:
                    player = (models.Player.objects.qualified(start, end)
                        .select_related('alias__profile')
                        .filter(alias__profile__name__isnull=False)
                        .values('alias__profile')
                        .annotate(num=agg_obj)
                        .filter(num__isnull=False)
                        .order_by('-num')[0:1]
                        .get()
                    )
                except ObjectDoesNotExist:
                    pass
                else:
                    summary.append({
                        'title': title,
                        'profile': player['alias__profile'],
                        'points': player['num'],
                        'points_translated': translate(player['num'])
                    })
            # prefetch profile instances
            qs = models.Profile.objects.select_related('loadout')
            pks = [entry['profile'] for entry in summary]
            prefetched = {obj.pk: obj for obj in list(qs.filter(pk__in=pks))}

            # replace profile pks with actual Profile instances
            for entry in summary:
                entry['profile'] = prefetched[entry['profile']]

            return {
                'title': period_title,
                'object_list': summary,
            }
        return _get_summary()


class TopListView(AnnualViewMixin, generic.ListView):
    template_name = 'tracker/chapters/top/top.html'
    model = models.Rank

    # list of categories
    boards = (
        (const.STATS_SCORE, _('Score'), 'int'),
        (const.STATS_SPM, ('Score/Minute'), 'ratio'),
        #(const.STATS_KDR, ('Kills/Deaths'), 'ratio'),
        (const.STATS_TIME, ('Time Played'), 'time'),
        (const.STATS_COOP_SCORE, ('CO-OP Score'), 'int'),
    )

    # limit of players per category
    limit = 5

    def get_queryset(self, *args, **kwargs):
        return (super(TopListView, self).get_queryset(*args, **kwargs)
            .select_related('profile', 'profile__loadout', 'profile__game_last')
            .filter(position__isnull=False, year=self.year)
            .order_by('position')
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super(TopListView, self).get_context_data(*args, **kwargs)
        context_data.update(self.get_objects())
        return context_data

    def get_objects(self):
        boards = []
        qs = (self.get_queryset()
            .filter(
                # get the ids of the specified categories
                category__in=map(lambda board: board[0], self.boards), 
                position__lte=self.limit
            )
        )
        for leaderboard, title, type in self.boards:
            # get a list of ranked players for each specified leaderboard
            objects = []
            for obj in qs:
                # append profiles with the same leaderboard type
                if obj.category == leaderboard:
                    objects.append(obj)
            boards.append((definitions.STATS[leaderboard], title, type, objects))
        return {'boards': boards}


class BoardListView(TopListView):
    template_name = 'tracker/chapters/leaderboard/leaderboard.html'
    paginate_by = 20

    boards = (
        # Group name:
        #   stat id, human_name, stat display type
        #   
        # the url/context name is obtained with defitions.STATS dict
        [_('Score'), (
            (const.STATS_SCORE, _('Score'), 'int'),
            (const.STATS_TIME, _('Time Played'), 'time'),
            (const.STATS_WINS, _('Wins'), 'int'),
            (const.STATS_SPM, _('Score/Minute'), 'ratio'),
            (const.STATS_SPR, _('Score/Round'), 'ratio'),
            (const.STATS_TOP_SCORE, _('Best Score'), 'int'),
        )],
        [_('Kills'), (
            (const.STATS_KILLS, _('Kills'), 'int'),
            (const.STATS_ARRESTS, _('Arrests'), 'int'),
            #(const.STATS_TOP_KILLS, _('Top Kills'), 'int'),
            #(const.STATS_TOP_ARRESTS, _('Top Arrests'), 'int'),
            (const.STATS_KDR, _('K/D Ratio'), 'ratio'),
            (const.STATS_AMMO_ACCURACY, _('Accuracy'), 'percent'),
            (const.STATS_KILL_STREAK, _('Best Kill Streak'), 'int'),
            (const.STATS_ARREST_STREAK, _('Best Arrest Streak'), 'int'),
        )],
        [_('VIP Escort'), (
            (const.STATS_VIP_ESCAPES, _('VIP Escapes'), 'int'),
            (const.STATS_VIP_CAPTURES, _('VIP Captures'), 'int'),
            (const.STATS_VIP_RESCUES, _('VIP Rescues'), 'int'),
            (const.STATS_VIP_KILLS_VALID, _('VIP Kills'), 'int'),
        )],
        # [_('Rapid Deployment'), (
        #     (const.STATS_RD_BOMBS_DEFUSED, _('Bombs Disarmed'), 'int'),
        # )],
        # [_('Smash and Grab'), (
        #     (const.STATS_SG_ESCAPES, _('Case Escapes'), 'int'),
        #     (const.STATS_SG_KILLS, _('Case Carrier Kills'), 'int'),
        # )],
        [_('CO-OP'), (
            (const.STATS_COOP_SCORE, _('Score'), 'int'),
            (const.STATS_COOP_TIME, _('Time Played'), 'time'),
            (const.STATS_COOP_GAMES, _('Missions Attempted'), 'int'),
            (const.STATS_COOP_WINS, _('Missions Completed'), 'int'),
            (const.STATS_COOP_ENEMY_ARRESTS, _('Suspects Arrested'), 'int'),
            (const.STATS_COOP_ENEMY_KILLS, _('Suspects Neutralized'), 'int'),
            #(const.STATS_COOP_HOSTAGE_ARRESTS, _('Civilians Arrested'), 'int'),
        )],
    )
    board_name_default = 'score'

    def __init__(self, *args, **kwargs):
        super(BoardListView, self).__init__(*args, **kwargs)
        self.board_list = self.get_boards()

    def get(self, *args, **kwargs):
        """Set the active leaderboard."""
        board_name = self.kwargs.get('board_name', None)
        # set default
        if not board_name:
            board_name = self.board_name_default
        # check the selected board name
        if board_name not in self.board_list:
            raise Http404
        # get the board details
        self.board = self.board_list[board_name]
        return super(BoardListView, self).get(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return (super(BoardListView, self).get_queryset(*args, **kwargs)
            .filter(category=self.board['id'])
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super(BoardListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'board_list': self.board_list,
            'board': self.board,
        })
        return context_data

    @classmethod
    def get_boards(cls):
        """
        Return an ordered dict mapping stat categories to leaderboard extended details.
        """
        leadeboards = collections.OrderedDict()
        for category, boards in cls.boards:
            for (stat_id, title, type) in boards:
                # e.g. {'vip_kills': {'category': 'VIP Escort', ..},..}
                leadeboards[definitions.STATS[stat_id]] = {
                    'id': stat_id,
                    'name': definitions.STATS[stat_id],
                    'category': category,
                    'title': title,
                    'type': type,
                }
        return leadeboards

    def get_objects(self):
        return {}


class GameListBaseView(FeaturedViewMixin, generic.ListView):
    limit = 10


class GameListView(FilterViewMixin, GameListBaseView):
    template_name = 'tracker/chapters/game/list_history.html'
    model = models.Game
    paginate_by = 50

    form_class = forms.GameFilterForm
    form = None

    def get(self, request, *args, **kwargs):
        self.form = self.form_class(data=request.GET)
        return super(GameListView, self).get(request, *args, **kwargs) 

    def get_context_data(self, *args, **kwargs):
        context_data = super(GameListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'form': self.form,
        })
        return context_data

    def get_queryset(self, *args, **kwargs):
        # cache the result
        qs = super(GameListView, self).get_queryset(*args, **kwargs)
        # only do further lookup if the form is bound and valid
        if not self.form.is_valid():
            return qs.none()
        # filter by map
        if self.form.cleaned_data.get('mapname', None):
            qs = qs.filter(mapname=self.form.cleaned_data['mapname'])
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
                qs = qs.filter(player__alias__name__iexact=name)
        # filter by year
        if self.form.cleaned_data.get('year', None):
            qs = qs.filter(date_finished__year=self.form.cleaned_data['year'])
        # filter by month
        if self.form.cleaned_data.get('month', None):
            qs = qs.filter(date_finished__month=self.form.cleaned_data['month'])
        # filter by day
        if self.form.cleaned_data.get('day', None):
            qs = qs.filter(date_finished__day=self.form.cleaned_data['day'])
        # cache the queryset
        return qs.order_by('-date_finished')  # .distinct()  #.cache()


class GameOnlineListView(GameListBaseView):
    template_name = 'tracker/chapters/game/list_online.html'
    model = models.Server
    paginate_by = 50

    def get_queryset(self):
        """Return a list of ServerStatus objects."""
        return self.model.objects.status.filter(player_num='[1-9]*').sort('-player_num')


class GameDetailView(generic.DetailView):
    TEMPLATE_DEFAULT = 'tracker/chapters/game/detail.html'
    TEMPLATE_MODE = 'tracker/chapters/game/detail_mode%(mode)s.html'

    pk_url_kwarg = 'game_id'
    model = models.Game

    categories = {
        'all': (
            ('score', _('Highest Score'), ngettext_lazy('%d point', '%d points')),
            ('kills', _('Most Kills'), ngettext_lazy('%d kill', '%d kills')),
            ('arrests', _('Most Arrests'), ngettext_lazy('%d arrest', '%d arrests')),
            ('ammo_accuracy', _('Highest Accuracy'), _('%d%%')),
            ('ammo_shots', _('Most Ammo Fired'), ngettext_lazy('%d bullet', '%d bullets')),
            ('kill_streak', _('Highest Kill Streak'), ngettext_lazy('%d kill', '%d kills')),
            ('arrest_streak', _('Highest Arrest Streak'), ngettext_lazy('%d arrest', '%d arrests')),
        ),
        definitions.MODE_VIP: (
            ('vip_captures', _('Most VIP captures'), ngettext_lazy('%d capture', '%d captures')),
            ('vip_rescues', _('Most VIP rescues'), ngettext_lazy('%d rescue', '%d rescues')),
        ),
    }

    def get_template_names(self, *args, **kwargs):
        return [self.TEMPLATE_MODE % {'mode': self.object.gametype}, self.TEMPLATE_DEFAULT]

    def get_context_data(self, *args, **kwargs):
        players = sorted(
            models.Player.objects.prefetched().filter(game=self.object.pk), 
            # sort by score, kills, arrests, -deaths
            key=lambda player: (player.score, player.kills, player.arrests, -player.deaths), 
            reverse=True
        )
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

            'players_best': self.get_best_players(players),

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
        return (super(GameDetailView, self).get_queryset(*args, **kwargs).select_related('server'))

    def get_close_games(self):
        "Return the games preceding and following this one."
        qs = models.Game.objects.filter(server=self.object.server)
        return {
            'previous': qs.filter(pk__lt=self.object.pk).order_by('-pk').first(),
            'next': qs.filter(pk__gt=self.object.pk).order_by('pk').first(),
        }

    def get_best_players(self, players):
        categories = []
        best = []

        # append common stats
        categories.extend(self.categories['all'])
        # append mode specific stats
        if self.object.gametype in self.categories:
            categories.extend(self.categories[self.object.gametype])

        for category, category_translated, points_translated in categories:
            sortable = sorted(players, key=utils.sort_key(category), reverse=True)
            player = next(iter(sortable), None)
            if player:
                points = getattr(player, category)
                # only add the player if he/she has actually earned some points
                if points:
                    best.append({
                        'category': category,
                        'category_translated': category_translated, 
                        'player': player,
                        'points': points,
                        'points_translated': points_translated % points,
                    })
        # shuffile
        random.shuffle(best)
        return best

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


class ServerListView(FilterViewMixin, generic.ListView):
    FETCH_INTERVAL = 10  # ajax update interval

    template_name = 'tracker/chapters/server/list.html'
    model = models.Server
    form_class = forms.ServerFilterForm
    form = None

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super(ServerListView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.form = self.form_class(data=request.GET)
        return super(ServerListView, self).get(request, *args, **kwargs) 

    def get_queryset(self, *args, **kwargs):
        if not self.form.is_valid():
            return super(ServerListView, self).get_queryset(*args, **kwargs).none()
        # assemble filters
        filters = {}
        # filter empty servers
        if self.form.cleaned_data.get('filter_empty', None):
            filters['is_empty'] = False
        # filter full servers
        if self.form.cleaned_data.get('filter_full', None):
            filters['is_full'] = False
        # filter password protected servers
        if self.form.cleaned_data.get('filter_passworded', None):
            filters['passworded'] = False
        # filter by game label
        if self.form.cleaned_data.get('gamename', None) is not None:
            filters['gamename'] = utils.escape_cache_key(self.form.cleaned_data['gamename'])
        # filter by game version
        if self.form.cleaned_data.get('gamever', None) is not None:
            filters['gamever'] = utils.escape_cache_key(self.form.cleaned_data['gamever'])
        # filter servers by gametype
        if self.form.cleaned_data.get('gametype', None) is not None:
            filters['gametype'] = utils.escape_cache_key(self.form.cleaned_data['gametype'])
        # then apply them
        return self.model.objects.status.filter(**filters).sort('-player_num')

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServerListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'FETCH_INTERVAL': self.FETCH_INTERVAL,
            'form': self.form,
        })
        return context_data


class ServerListAjaxView(ServerListView):
    template_name = 'tracker/chapters/server/list_ajax.html'


class ServerDetailView(generic.DetailView):
    FETCH_INTERVAL = 5  # ajax update interval
    TEMPLATE_DEFAULT = 'tracker/chapters/server/detail.html'
    TEMPLATE_MODE = 'tracker/chapters/server/detail_mode%(mode)s.html'

    model = models.Server

    class ServerNotAvailable(Exception):
        pass

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super(ServerDetailView, self).dispatch(*args, **kwargs)

    def get_template_names(self, *args, **kwargs):
        return [self.TEMPLATE_MODE % {'mode': self.status.gametype}, self.TEMPLATE_DEFAULT]

    def get(self, request, *args, **kwargs):
        try:
            response = super(ServerDetailView, self).get(request, *args, **kwargs)
        except self.ServerNotAvailable:
            return render(request, 'tracker/chapters/server/cap.html', {})
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

        if not (obj.enabled and obj.listed):
            raise self.ServerNotAvailable

        # attempt to fetch cached server status
        try:
            self.status = obj.status
            assert self.status
        except AssertionError:
            raise self.ServerNotAvailable

        return obj

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServerDetailView, self).get_context_data(*args, **kwargs)

        # sort players by score, kills, arrests, -deaths
        players = sorted(
            self.status.players, 
            key=lambda player: (player.get('score', 0), player.get('kills', 0), player.get('arrests', 0), -player.get('deaths', 0)),
            reverse=True
        )

        context_data.update({
            'FETCH_INTERVAL': self.FETCH_INTERVAL,
            'status': self.status,
            'players': players,
            'players_blue': [player for player in players if player['team'] == definitions.TEAM_BLUE],
            'players_red': [player for player in players if player['team'] == definitions.TEAM_RED],
        })
        return context_data


class ServerDetailAjaxView(ServerDetailView):
    TEMPLATE_DEFAULT = 'tracker/chapters/server/detail_ajax.html'
    TEMPLATE_MODE = 'tracker/chapters/server/detail_mode%(mode)s_ajax.html'

    def get(self, request, *args, **kwargs):
        """
        Override the server ajax view so it does not return 
        the SWAT black screen message in case of an error.

        Return 404 instead.
        """
        try:
            response = super(ServerDetailView, self).get(request, *args, **kwargs)
        except self.ServerNotAvailable:
            raise Http404('The server is not available.')
        else:
            return response


class ProfileBaseView(AnnualViewMixin, generic.DetailView):
    RECENT_TIME = 60*60*24
    RECENT_MAX = 50
    RECENT_MAX_MAPS = 5

    award_list = (
        (const.STATS_SPM, 
            ngettext_lazy(
                'Best score/minute ratio in %(year)s',
                '%(ordinal)s best score/minute ratio in %(year)s',
                'position'
            )
        ),
        (const.STATS_SPR, 
            ngettext_lazy(
                'Best score/round ratio in %(year)s',
                '%(ordinal)s best score/round ratio in %(year)s',
                'position'
            )
        ),
        (const.STATS_KDR, 
            ngettext_lazy(
                'Best kills/deaths ratio in %(year)s',
                '%(ordinal)s best kills/deaths ratio in %(year)s',
                'position'
            )
        ),
        (const.STATS_AMMO_ACCURACY, 
            ngettext_lazy(
                'Highest accuracy in %(year)s',
                '%(ordinal)s highest accuracy in %(year)s',
                'position'
            )
        ),
        (const.STATS_SCORE, 
            ngettext_lazy(
                'Highest score in %(year)s',
                '%(ordinal)s highest score in %(year)s',
                'position'
            )
        ),
        (const.STATS_TOP_SCORE, 
            ngettext_lazy(
                'Highest round score in %(year)s',
                '%(ordinal)s highest round score in %(year)s',
                'position'
            )
        ),
        (const.STATS_TIME, 
            ngettext_lazy(
                'Highest playtime in %(year)s',
                '%(ordinal)s highest playtime in %(year)s',
                'position'
            )
        ),
        (const.STATS_KILLS, 
            ngettext_lazy(
                'Most kills in %(year)s',
                '%(ordinal)s most kills in %(year)s',
                'position'
            )
        ),
        (const.STATS_ARRESTS, 
            ngettext_lazy(
                'Most arrests in %(year)s',
                '%(ordinal)s most arrests in %(year)s',
                'position'
            )
        ),
        (const.STATS_KILL_STREAK, 
            ngettext_lazy(
                'Highest kill streak in %(year)s',
                '%(ordinal)s highest kill streak in %(year)s',
                'position'
            )
        ),
        (const.STATS_VIP_ESCAPES, 
            ngettext_lazy(
                'Most VIP escapes in %(year)s',
                '%(ordinal)s most VIP escapes in %(year)s',
                'position'
            )
        ),
        (const.STATS_VIP_CAPTURES, 
            ngettext_lazy(
                'Most VIP captures in %(year)s',
                '%(ordinal)s most VIP captures in %(year)s',
                'position'
            )
        ),
        (const.STATS_VIP_RESCUES, 
            ngettext_lazy(
                'Most VIP rescues in %(year)s',
                '%(ordinal)s most VIP rescues in %(year)s',
                'position'
            )
        ),
        (const.STATS_COOP_SCORE, 
            ngettext_lazy(
                'Highest CO-OP score in %(year)s',
                '%(ordinal)s highest CO-OP score in %(year)s',
                'position'
            )
        ),
        (const.STATS_COOP_WINS, 
            ngettext_lazy(
                'Most CO-OP missions completed in %(year)s',
                '%(ordinal)s most CO-OP missions completed in %(year)s',
                'position'
            )
        ),
        (const.STATS_COOP_TIME, 
            ngettext_lazy(
                'Highest CO-OP playtime in %(year)s',
                '%(ordinal)s highest CO-OP playtime in %(year)s',
                'position'
            )
        ),
    )

    # max position which can be nominated for an award
    award_max_position = 5

    class ProfileNotPrepared(Exception): 
        pass

    model = models.Profile
    pk_url_kwarg = 'profile_id'

    def get(self, request, *args, **kwargs):
        """
        Retrive the requested profile entry.

        If the entry appears to be empty (i.e. no popular name, loadout, etc set),
        return a "Profile not available error page".
        """
        try:
            response = super(ProfileBaseView, self).get(request, *args, **kwargs)
        except self.ProfileNotPrepared:
            return render(request, 'tracker/chapters/profile/cap.html', {})
        else:
            # redirect to the latest avaiable profile.. unless a year is specified
            if not kwargs.get('year') and self.object.last_seen.year != self.year_now:
                return HttpResponseRedirect(
                    templatetags.profile_url(self.object, request.resolver_match.view_name, **{'year': self.object.last_seen.year})
                )
            return response

    def get_queryset(self, *args, **kwargs):
        return (super(ProfileBaseView, self).get_queryset(*args, **kwargs)
            .select_related('loadout', 'game_first', 'game_last')
        )

    def get_object(self, *args, **kwargs):
        """
        Obtain the object instance by calling the parent get_object method.

        In case the profile object is not considered popular 
        (i.e. it has no popular name or team set), raise ProfileBaseView.ProfileNotPrepared.
        """
        obj = super(ProfileBaseView, self).get_object(*args, **kwargs)
        if not obj.popular:
            raise self.ProfileNotPrepared
        return obj

    def get_context_data(self, *args, **kwargs):
        # limit the years list with the range of years the player played in
        self.years = list(range(self.object.first_seen.year, self.object.last_seen.year + 1))
        context_data = super(ProfileBaseView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'recent': self.get_recent_games(),
            'award': self.get_award(),
            #'all': self.object.aggregate_mode_stats(models.Profile.SET_STATS_ALL, *models.Rank.get_period_for_now()),
        })
        return context_data

    def get_games(self):
        """Return a queryset of profile related games sorted by id in descending order."""
        return models.Game.objects.filter(player__alias__profile=self.object)

    def get_recent_games(self):
        """
        Return a LIST of the latest profile related games limited by
        ProfileBaseView.GAMES_RECENT_MAX or ProfileBaseView.MAPS_RECENT_MAX (whichever is lower).
        """
        @cacheops.cached(timeout=60*5, extra=self.object.pk)
        def _get_recent_games():
            recent = []
            map_count = 0
            map_name = None
            min_date = self.object.game_last.date_finished - datetime.timedelta(seconds=self.RECENT_TIME)
            games = (self.get_games()
                .filter(date_finished__gte=min_date, date_finished__lte=self.object.game_last.date_finished)
                .order_by('-date_finished')
            )[:self.RECENT_MAX]
            # attempt to limit the number of displayed games by a number of maps
            for game in games:
                if game.mapname != map_name:
                    map_name = game.mapname
                    map_count += 1
                if map_count > self.RECENT_MAX_MAPS:
                    break
                recent.append(game)
            return recent
        return _get_recent_games()

    def get_stats(self):
        """
        Return a DICT of the profile related rank cached stats.

        Example:
            {'score': 123, 'kills': 345, ...}
        """
        stored = {}
        # turn the id => name tuple into a dict
        mapping = dict(definitions.STATS)
        for score in self.object.rank_set.filter(year=self.year):
            stored[score.category] = score.points
        # set zeroes to the rest of the categories
        return {value: stored[key] if key in stored else 0.0 for key, value in six.iteritems(mapping)}

    def get_award(self):
        """
        Return the first matching ranking position from the leaderboards specified in `rank_list` 
        """
        @cacheops.cached(timeout=60*60, extra=self.object.pk)
        def _get_award():
            # get the category ids
            categories = tuple(map(lambda entry: entry[0], self.award_list))
            qs = (models.Rank.objects
                .filter(
                    profile=self.object,
                    position__lte=self.award_max_position,
                    category__in=categories,
                )
            )
            # sort entries of the same position by rank_list in asecending order and years in descending order
            # return the very first entry
            key = lambda entry: (entry.position, categories.index(entry.category), -entry.year)
            return next(iter(sorted(qs, key=key)), None)

        award = _get_award()
        if award:
            for category, text in self.award_list:
                if award.category == category:
                    return {
                        'title': text % {
                            'ordinal': humanize.ordinal(award.position), 
                            'position': award.position, 
                            'year': award.year
                        },
                        'obj': award,
                    }
        return None


class ProfileDetailView(ProfileBaseView):
    template_name = 'tracker/chapters/profile/overview.html'

    def get_context_data(self, *args, **kwargs):
        stats = self.get_stats()
        maps = []  #self.get_maps()

        context_data = super(ProfileDetailView, self).get_context_data(*args, **kwargs)
        context_data.update({
            # calculate rank
            'rank': utils.Rank(definitions.RANKS, stats['score']),
            # combine rank stats with weapon based stats
            'stats': stats,
            # get the players best games
            'best': (
                (
                    _('First Appearance'), 
                    self.object.game_first, 
                    humanize.naturaltime(self.object.game_first.date_finished)
                ),
                (
                    _('Best Score'), 
                    self.get_best_game('score', stats['top_score']),
                    (ngettext_lazy('%(points)s point', '%(points)s points', int(stats['top_score'])) 
                        % {'points': int(stats['top_score'])}
                    )
                ),
                (
                    _('Top Kills'), 
                    self.get_best_game('kills', stats['top_kills']),
                    (ngettext_lazy('%(points)d kill', '%(points)d kills', int(stats['top_kills'])) 
                        % {'points': int(stats['top_kills'])}
                    )
                ),
                (
                    _('Top Arrests'), 
                    self.get_best_game('arrests', stats['top_arrests']),
                    (ngettext_lazy('%(points)d arrest', '%(points)d arrests', int(stats['top_arrests'])) 
                        % {'points': int(stats['top_arrests'])}
                    )
                ),
                (
                    _('Best Kill Streak'), 
                    self.get_best_game('kill_streak', stats['kill_streak']),
                    (ngettext_lazy('%(points)d kill in a row', '%(points)d kills in a row', int(stats['kill_streak'])) 
                        % {'points': int(stats['kill_streak'])}
                    )
                ),
                (
                    _('Best Arrest Streak'), 
                    self.get_best_game('arrest_streak', stats['arrest_streak']),
                    (ngettext_lazy('%(points)d arrest in a row', '%(points)d arrests in a row', int(stats['arrest_streak'])) 
                        % {'points': int(stats['arrest_streak'])}
                    )
                ),
            ),
            # maps + best maps
            'map_list': maps,
            'map_best': utils.rank_dicts(maps),
            # get player wide max ratio values
            'max': self.get_max(),
        })
        return context_data

    def get_maps(self):
        """Aggegate map stats."""
        items = {
            'time': (
                aggregate_if.Sum(
                    'time', 
                    only=Q(game__gametype__in=definitions.MODES_VERSUS)
                )
            ),
            'games': (
                aggregate_if.Count(
                    'game', 
                    only=Q(game__gametype__in=definitions.MODES_VERSUS),
                    distinct=True
                )
            ),
            'overall_score': db.models.Sum('score'),
            'best_score': db.models.Max('score'),
            'kills': db.models.Sum('kills'),
            'deaths': (
                aggregate_if.Sum(
                    'deaths', 
                    only=Q(game__gametype__in=definitions.MODES_VERSUS)
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
        def _get_maps():
            period = models.Rank.get_period_for_year(self.year)
            aggregated = self.object.aggregate(items, *period, group_by='game__mapname', group_by_as='mapname')
            return [item for item in aggregated if item['games']]
        return _get_maps()

    def get_best_game(self, field, points):
        """
        Return a Player instance with `field` equal to `points`.
        """
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, field, self.year))
        def _get_best_game():
            try:
                assert points > 0
                period = models.Rank.get_period_for_year(self.year)
                player = (self.object.qualified(*period)
                    .select_related('game')
                    .filter(**{field: points})[:1]
                    .get()
                )
            except (AssertionError, ObjectDoesNotExist):
                return None
            else:
                return player.game
        return _get_best_game()

    def get_best_weapon(self, aggregated):
        """Return the weapon with most kills."""
        return next(iter(sorted(six.itervalues(aggregated), key=lambda weapon: weapon['kills'], reverse=True)), None)

    def get_max(self, *categories):
        "Return the max values for the K/D and S/M stats."
        @cacheops.cached(timeout=60*60*24)
        def _get_max():
            return (models.Rank.objects
                .filter(year=self.year)
                .aggregate(
                    spm=aggregate_if.Max('points', only=Q(category=const.STATS_SPM)),
                    kdr=aggregate_if.Max('points', only=Q(category=const.STATS_KDR))
                )
            )
        return _get_max()


class ProfileWeaponListView(ProfileBaseView):
    
    template_name = 'tracker/chapters/profile/equipment.html'

    def get_context_data(self, *args, **kwargs):
        # get a list of used weapons (ie a weapon with at least one kill or a shot)
        weapons = {
            weapon: stats for weapon, stats in six.iteritems(self.get_weapons()) 
            if stats['kills'] or stats['shots']
        }
        # sort primary and secondary weapons by accuracy
        primary = sorted(
            self.filter_weapons(definitions.WEAPONS_PRIMARY, weapons).values(), 
            key=lambda weapon: weapon['accuracy'],
            reverse=True
        )
        secondary = sorted(
            self.filter_weapons(definitions.WEAPONS_SECONDARY, weapons).values(), 
            key=lambda weapon: weapon['accuracy'],
            reverse=True
        )
        # sort tactical weapons by number of shots
        tactical = sorted(
            self.filter_weapons(definitions.WEAPONS_TACTICAL, weapons).values(),
            key=lambda weapon: weapon['shots'],
            reverse=True
        )
        context_data = super(ProfileWeaponListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'primary': primary,
            'primary_best': utils.rank_dicts(primary),
            'secondary': secondary,
            'secondary_best': utils.rank_dicts(secondary),
            'tactical': tactical, 
            'tactical_best': utils.rank_dicts(tactical),
            # retrieve the most popular loadout for the selected year
            # unless the selected year is the current year
            'loadout': self.object.loadout if (self.year == self.year_now) else self.get_favourite_loadout(),
        })
        return context_data

    def get_weapons(self):
        """
        Return weapon usage stats dict for non-COOP gamemodes.

        Example:
            {0: {'name': 0, 'kills': 123, ...}, 1: {...}, ...}
        """
        @cacheops.cached(timeout=60*60*24, extra=(self.object.pk, self.year))
        def _get_weapons():
            aggregated = self.object.aggregate_weapon_stats(
                *models.Rank.get_period_for_year(self.year), 
                filters={'game__gametype__in': definitions.MODES_VERSUS}
            )
            return aggregated
        return _get_weapons()

    def get_favourite_loadout(self):
        @cacheops.cached(timeout=60*60*24, extra=(self.object.pk, self.year))
        def _get_favourite_loadout():
            return self.object.fetch_popular_loadout(year=self.year)
        return _get_favourite_loadout()

    @staticmethod
    def filter_weapons(pattern, weapons):
        filtered = {}
        for weapon in weapons:
            # check whether the weapon code is in the unmapped pattern tuple
            if int(weapon) in pattern:
                filtered[weapon] = weapons[weapon]
        return filtered


class ProfileCoopDetailView(ProfileBaseView):
    template_name = 'tracker/chapters/profile/coop.html'

    def get_context_data(self, *args, **kwargs):
        context_data = super(ProfileCoopDetailView, self).get_context_data(*args, **kwargs)

        maps = self.get_maps()
        equipment = self.get_favourite_equipment()
        # annotate with fav equipment
        for item in maps:
            item['loadout'] = equipment[item['mapname']] if item['mapname'] in equipment else None

        context_data.update({
            'stats':self.get_stats(),
            'maps': maps,
        })
        return context_data

    def get_maps(self):
        items = {
            # best coop score
            'score_best': (
                db.models.Max('game__coop_score')
            ),
            # average coop score
            'score_avg': (
                db.models.Avg('game__coop_score')
            ),
            # average mission time
            'time_avg': (
                aggregate_if.Min(
                    'game__time', 
                    only=Q(game__outcome__in=definitions.COMPLETED_MISSIONS)
                )
            ),
            # best mission time
            'time_best': (
                aggregate_if.Min(
                    'game__time', 
                    only=Q(game__outcome__in=definitions.COMPLETED_MISSIONS)
                )
            ),
            # total number of missions completed
            'missions_completed': (
                aggregate_if.Count(
                    'game', 
                    only=Q(game__outcome__in=definitions.COMPLETED_MISSIONS),
                    distinct=True
                )
            ),
            # total number of missions failed
            'missions_failed': (
                aggregate_if.Count('game', 
                    only=Q(game__outcome__in=definitions.FAILED_MISSIONS),
                    distinct=True
                )
            ),
        }
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _coop_get_maps():
            aggregated = self.object.aggregate(
                items, 
                *models.Rank.get_period_for_year(self.year), 
                group_by='game__mapname',
                group_by_as='mapname',
                filters={'game__gametype__in': definitions.MODES_COOP, 'dropped': False}
            )
            return [item for item in aggregated if item['time_best']]
        return _coop_get_maps()

    def get_favourite_equipment(self):
        @cacheops.cached(timeout=60*60, extra=(self.object.pk, self.year))
        def _coop_get_favourite_equipment():
            maps = {}
            period = models.Rank.get_period_for_year(self.year)
            aggregated = (self.object
                .qualified(*period)
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


class ProfileRankingListView(ProfileBaseView, generic.list.MultipleObjectMixin):
    template_name = 'tracker/chapters/profile/ranking.html'

    def get_context_data(self, *args, **kwargs):
        self.object_list = self.get_ranks()
        context_data = super(ProfileRankingListView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'rank_list': self.object_list,
        })
        return context_data

    def get_ranks(self):
        categories = []
        # lend board list from the Leaderboad view
        ranks = BoardListView.get_boards()
        # set defaults and acqure a list of categories
        for details in six.itervalues(ranks):
            details.update({
                'points': 0,
                'position': None,
            })
            categories.append(details['id'])

        entries = (models.Rank.objects
            .filter(
                profile=self.object, 
                year=self.year, 
                category__in=categories
            )
        )
        # set the extra 'points' and 'position' dict item to leaderboards the player has been ranked in
        for entry in entries:
            ranks[definitions.STATS[entry.category]].update({
                'points': entry.points,
                'position': entry.position,
            })
        return ranks


class ProfileHistoryListView(ProfileBaseView, generic.list.MultipleObjectMixin):
    template_name = 'tracker/chapters/profile/history.html'
    paginate_by = 50
    object_list = None

    def get_context_data(self, *args, **kwargs):
        start, end = models.Rank.get_period_for_year(self.year)
        # for paginator
        self.object_list = (self.get_games()
            .filter(date_finished__gte=start, date_finished__lte=end)
            .order_by('-date_finished')
        )
        context_data = super(ProfileHistoryListView, self).get_context_data(*args, **kwargs)
        return context_data


class PlayerSearchView(FilterViewMixin, generic.ListView):
    template_name = 'tracker/chapters/search/search.html'
    model = models.Alias
    paginate_by = 20
    form_class = forms.PlayerSearchForm
    form = None

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super(PlayerSearchView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.form = self.form_class(data=request.GET or None)
        return super(PlayerSearchView, self).get(request, *args, **kwargs) 

    def get_queryset(self, *args, **kwargs):
        qs = super(PlayerSearchView, self).get_queryset(*args, **kwargs)
        if not self.form.is_valid():
            return qs.none()
        # search by player name
        return (qs
            .select_related('profile', 'profile__game_last', 'profile__loadout')
            .filter(
                name__icontains=self.form.cleaned_data['player'],
                profile__game_last__isnull=False,
                profile__name__isnull=False,
                profile__team__isnull=False
            )
            .order_by('-profile__game_last__date_finished')
            .distinct('profile__game_last__date_finished', 'profile')
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super(PlayerSearchView, self).get_context_data(*args, **kwargs)
        context_data.update({
            'form': self.form,
            'term_random': self.get_random_name(),
        })
        return context_data

    def get_random_name(self):
        @cacheops.cached(timeout=60*60)
        def _get_random_name():
            queryset = models.Profile.objects.filter(name__isnull=False)
            try:
                profile = queryset[random.randrange(1, queryset.count())]
            except (IndexError, ValueError):
                return None
            return profile.name
        return _get_random_name()


class ProfileRedirectView(generic.RedirectView):
    """Redirect /player/Name/ requests to the search view."""

    def get_redirect_url(self, *args, **kwargs):
        return '%s?player=%s' % (reverse('tracker:search'), kwargs.get('name', ''))