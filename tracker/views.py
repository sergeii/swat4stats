import datetime
import random
import logging
import collections

from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.views import generic
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext_lazy, gettext_lazy as _
from django import db
from django.utils import timezone
from django.contrib.humanize.templatetags import humanize
from django.views.decorators.cache import never_cache
from django.db.models import Q, Max, Min, Sum, Avg, Count, When, Case

from . import models, forms, definitions, utils, templatetags, jobs
from .definitions import STAT

logger = logging.getLogger(__name__)


class AnnualViewMixin:
    # min days since jan 01 the new year will not consider interesting (since lack of data)
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
        super().__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        if not kwargs.get('year'):
            start_of_the_year = models.Rank.get_period_for_year(self.year_max)[0]
            # skip the current year if it's too early...
            if (timezone.now() - start_of_the_year).days < self.MIN_YEAR_DAYS and len(self.years) > 1:
                # ...unless it's the only year
                self.year = self.years[-2]
            else:
                self.year = self.years[-1]
        else:
            self.year = int(kwargs['year'])
        # raise 404 if the year is not in the list
        if self.year not in self.years:
            raise Http404(_('%(year)s is not a valid year.') % {'year': self.year})
        return super().get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
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
        return jobs.get_min_year()


class FilterViewMixin:

    def get_context_data(self, *args, **kwargs):
        filters = self.request.GET.copy()

        if 'page' in filters:
            del filters['page']

        context_data = super().get_context_data(*args, **kwargs)
        context_data.update({
            'filters': filters,
        })
        return context_data


class FeaturedViewMixin(AnnualViewMixin):
    sample = 20
    limit = 10
    min_time = 600
    min_score = 200

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        context_data.update({
            'featured': self.get_featured_games(),
        })
        return context_data

    def get_featured_period(self):
        return models.Rank.get_period_for_year(self.year)

    def get_featured_games(self):
        start, end = self.get_featured_period()

        if start is None:
            return None

        # get random offset
        offset = random.randint(0, self.sample)

        qs = (
            models.Game.objects
            .extra(
                select={
                    'score_total': 'score_swat + score_sus',
                    'score_avg': '(score_swat + score_sus) / time',
                },
                order_by=('-score_avg',),
                where=['score_swat + score_sus >= %s'],
                params=[self.min_score]
            )
            .filter(
                date_finished__gte=start,
                date_finished__lte=end,
                time__gte=self.min_time,
                player_num__gte=models.Profile.MIN_PLAYERS
            )
        )
        return qs[offset:offset+self.limit]


class TopListView(AnnualViewMixin, generic.ListView):
    template_name = 'tracker/chapters/top/top.html'
    model = models.Rank

    # list of categories
    boards = (
        (STAT.SCORE, _('Score'), 'int'),
        (STAT.SPM, ('Score/Minute'), 'ratio'),
        (STAT.TIME, ('Time Played'), 'time'),
        (STAT.COOP_SCORE, ('CO-OP Score'), 'int'),
    )

    # limit of players per category
    limit = 5

    def get_queryset(self, *args, **kwargs):
        return (
            super().get_queryset(*args, **kwargs)
            .select_related('profile', 'profile__loadout', 'profile__game_last')
            .filter(position__isnull=False, year=self.year)
            .order_by('position')
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        context_data.update(self.get_objects())
        return context_data

    def get_objects(self):
        boards = []
        qs = (
            self.get_queryset()
            .filter(
                # get the ids of the specified categories
                category__in=[board[0] for board in self.boards],
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
        # the url/context name is obtained with defitions.STATS dict
        [_('Score'), (
            (STAT.SCORE, _('Score'), 'int'),
            (STAT.TIME, _('Time Played'), 'hours'),
            (STAT.WINS, _('Wins'), 'int'),
            (STAT.SPM, _('Score/Minute'), 'ratio'),
            (STAT.SPR, _('Score/Round'), 'ratio'),
            (STAT.TOP_SCORE, _('Best Score'), 'int'),
        )],
        [_('Kills'), (
            (STAT.KILLS, _('Kills'), 'int'),
            (STAT.ARRESTS, _('Arrests'), 'int'),
            (STAT.KDR, _('K/D Ratio'), 'ratio'),
            (STAT.AMMO_ACCURACY, _('Accuracy'), 'percent'),
            (STAT.KILL_STREAK, _('Best Kill Streak'), 'int'),
            (STAT.ARREST_STREAK, _('Best Arrest Streak'), 'int'),
        )],
        [_('VIP Escort'), (
            (STAT.VIP_ESCAPES, _('VIP Escapes'), 'int'),
            (STAT.VIP_CAPTURES, _('VIP Captures'), 'int'),
            (STAT.VIP_RESCUES, _('VIP Rescues'), 'int'),
            (STAT.VIP_KILLS_VALID, _('VIP Kills'), 'int'),
        )],
        [_('Rapid Deployment'), (
            (STAT.RD_BOMBS_DEFUSED, _('Bombs Disarmed'), 'int'),
        )],
        [_('CO-OP'), (
            (STAT.COOP_SCORE, _('Score'), 'int'),
            (STAT.COOP_TIME, _('Time Played'), 'hours'),
            (STAT.COOP_GAMES, _('Missions Attempted'), 'int'),
            (STAT.COOP_WINS, _('Missions Completed'), 'int'),
            (STAT.COOP_ENEMY_ARRESTS, _('Suspects Arrested'), 'int'),
            (STAT.COOP_ENEMY_KILLS, _('Suspects Neutralized'), 'int'),
        )],
    )
    board_name_default = 'score'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_list = self.get_boards()

    def get(self, *args, **kwargs):
        """Set the active leaderboard."""
        board_name = self.kwargs.get('board_name')
        # set default
        if not board_name:
            board_name = self.get_default_board()
        # check the selected board name
        if board_name not in self.board_list:
            raise Http404
        # get the board details
        self.board = self.board_list[board_name]
        return super().get(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return (
            super().get_queryset(*args, **kwargs)
            .filter(category=self.board['id'])
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
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

    def get_default_board(self):
        return self.board_name_default


class ProfileBaseView(AnnualViewMixin, generic.DetailView):
    RECENT_TIME = 60*60*24
    RECENT_MAX = 50
    RECENT_MAX_MAPS = 5

    award_list = (
        (STAT.SPM,
            ngettext_lazy(
                'Best score/minute ratio in %(year)s',
                '%(ordinal)s best score/minute ratio in %(year)s',
                'position'
            )
         ),
        (STAT.SPR,
            ngettext_lazy(
                'Best score/round ratio in %(year)s',
                '%(ordinal)s best score/round ratio in %(year)s',
                'position'
            )
         ),
        (STAT.KDR,
            ngettext_lazy(
                'Best kills/deaths ratio in %(year)s',
                '%(ordinal)s best kills/deaths ratio in %(year)s',
                'position'
            )
         ),
        (STAT.AMMO_ACCURACY,
            ngettext_lazy(
                'Highest accuracy in %(year)s',
                '%(ordinal)s highest accuracy in %(year)s',
                'position'
            )
         ),
        (STAT.SCORE,
            ngettext_lazy(
                'Highest score in %(year)s',
                '%(ordinal)s highest score in %(year)s',
                'position'
            )
         ),
        (STAT.TOP_SCORE,
            ngettext_lazy(
                'Highest round score in %(year)s',
                '%(ordinal)s highest round score in %(year)s',
                'position'
            )
         ),
        (STAT.TIME,
            ngettext_lazy(
                'Highest playtime in %(year)s',
                '%(ordinal)s highest playtime in %(year)s',
                'position'
            )
         ),
        (STAT.KILLS,
            ngettext_lazy(
                'Most kills in %(year)s',
                '%(ordinal)s most kills in %(year)s',
                'position'
            )
         ),
        (STAT.ARRESTS,
            ngettext_lazy(
                'Most arrests in %(year)s',
                '%(ordinal)s most arrests in %(year)s',
                'position'
            )
         ),
        (STAT.KILL_STREAK,
            ngettext_lazy(
                'Highest kill streak in %(year)s',
                '%(ordinal)s highest kill streak in %(year)s',
                'position'
            )
         ),
        (STAT.VIP_ESCAPES,
            ngettext_lazy(
                'Most VIP escapes in %(year)s',
                '%(ordinal)s most VIP escapes in %(year)s',
                'position'
            )
         ),
        (STAT.VIP_CAPTURES,
            ngettext_lazy(
                'Most VIP captures in %(year)s',
                '%(ordinal)s most VIP captures in %(year)s',
                'position'
            )
         ),
        (STAT.VIP_RESCUES,
            ngettext_lazy(
                'Most VIP rescues in %(year)s',
                '%(ordinal)s most VIP rescues in %(year)s',
                'position'
            )
         ),
        (STAT.COOP_SCORE,
            ngettext_lazy(
                'Highest CO-OP score in %(year)s',
                '%(ordinal)s highest CO-OP score in %(year)s',
                'position'
            )
         ),
        (STAT.COOP_WINS,
            ngettext_lazy(
                'Most CO-OP missions completed in %(year)s',
                '%(ordinal)s most CO-OP missions completed in %(year)s',
                'position'
            )
         ),
        (STAT.COOP_TIME,
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
            response = super().get(request, *args, **kwargs)
        except self.ProfileNotPrepared:
            return render(request, 'tracker/chapters/profile/cap.html', {})
        else:
            # redirect to the latest avaiable profile.. unless a year is specified
            if not kwargs.get('year') and self.object.last_seen.year != self.year_now:
                return HttpResponseRedirect(
                    templatetags.profile_url(self.object,
                                             request.resolver_match.view_name,
                                             **{'year': self.object.last_seen.year})
                )
            return response

    def get_queryset(self, *args, **kwargs):
        return (
            super().get_queryset(*args, **kwargs)
            .select_related('loadout', 'game_first', 'game_last')
        )

    def get_object(self, *args, **kwargs):
        """
        Obtain the object instance by calling the parent get_object method.

        In case the profile object is not considered popular
        (i.e. it has no popular name or team set), raise ProfileBaseView.ProfileNotPrepared.
        """
        obj = super().get_object(*args, **kwargs)
        if not obj.popular:
            raise self.ProfileNotPrepared
        return obj

    def get_context_data(self, *args, **kwargs):
        # limit the years list with the range of years the player played in
        self.years = list(range(self.object.first_seen.year, self.object.last_seen.year + 1))
        context_data = super().get_context_data(*args, **kwargs)
        context_data.update({
            'recent': self.get_recent_games(),
            'award': self.get_award(),
        })
        return context_data

    def get_games(self):
        """Return a queryset of profile related games sorted by id in descending order."""
        return (
            models.Game.objects
            .filter(player__alias__profile=self.object)
            .order_by('-date_finished')
            .distinct('pk', 'date_finished')
        )

    def get_recent_games(self):
        """
        Return a LIST of the latest profile related games limited by
        ProfileBaseView.GAMES_RECENT_MAX or ProfileBaseView.MAPS_RECENT_MAX (whichever is lower).
        """
        recent = []
        min_date = self.object.game_last.date_finished - datetime.timedelta(seconds=self.RECENT_TIME)
        games = self.get_games().filter(date_finished__gte=min_date)[:self.RECENT_MAX]
        # limit by number of maps
        maps = set()
        for game in games:
            maps.add(game.mapname)
            recent.append(game)
            if len(maps) >= self.RECENT_MAX_MAPS:
                break
        return recent

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
        return {
            value: stored[key] if key in stored else 0.0
            for key, value in mapping.items()
        }

    def get_award(self):
        """
        Return the first matching ranking position from the leaderboards specified in `rank_list`
        """
        # get the category ids
        categories = tuple(map(lambda entry: entry[0], self.award_list))
        qs = (
            models.Rank.objects
            .filter(
                profile=self.object,
                position__lte=self.award_max_position,
                category__in=categories,
            )
        )

        # sort entries of the same position by rank_list in asecending order and years in descending order
        # return the very first entry
        ranked = sorted(qs, key=lambda e: (e.position, categories.index(e.category), -e.year))
        award = next(iter(ranked), None)

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
        maps = []  # self.get_maps()

        context_data = super().get_context_data(*args, **kwargs)
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
                     % {'points': int(stats['top_score'])}),
                ),
                (
                    _('Top Kills'),
                    self.get_best_game('kills', stats['top_kills']),
                    (ngettext_lazy('%(points)d kill', '%(points)d kills', int(stats['top_kills']))
                     % {'points': int(stats['top_kills'])}),
                ),
                (
                    _('Top Arrests'),
                    self.get_best_game('arrests', stats['top_arrests']),
                    (ngettext_lazy('%(points)d arrest', '%(points)d arrests', int(stats['top_arrests']))
                     % {'points': int(stats['top_arrests'])}),
                ),
                (
                    _('Best Kill Streak'),
                    self.get_best_game('kill_streak', stats['kill_streak']),
                    (ngettext_lazy('%(points)d kill in a row', '%(points)d kills in a row', int(stats['kill_streak']))
                     % {'points': int(stats['kill_streak'])})
                ),
                (
                    _('Best Arrest Streak'),
                    self.get_best_game('arrest_streak', stats['arrest_streak']),
                    (ngettext_lazy('%(points)d arrest in a row',
                                   '%(points)d arrests in a row',
                                   int(stats['arrest_streak']))
                     % {'points': int(stats['arrest_streak'])}),
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
        """Aggregate map stats."""
        items = {
            'time': (
                Sum(
                    Case(When(game__gametype__in=definitions.MODES_VERSUS, then='time'))
                )
            ),
            'games': (
                Count(
                    Case(When(game__gametype__in=definitions.MODES_VERSUS, then='game')),
                    distinct=True
                )
            ),
            'overall_score': Sum('score'),
            'best_score': Max('score'),
            'kills': Sum('kills'),
            'deaths': (
                Sum(
                    Case(When(game__gametype__in=definitions.MODES_VERSUS, then='deaths'))
                )
            ),
            'wins': (
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
            'losses': (
                Count(
                    Case(
                        When(
                            Q(team=definitions.TEAM_BLUE, game__outcome__in=definitions.SUS_GAMES) |
                            Q(team=definitions.TEAM_RED, game__outcome__in=definitions.SWAT_GAMES),
                            then='game'
                        )
                    ),
                    distinct=True
                )
            ),
        }
        period = models.Rank.get_period_for_year(self.year)
        aggregated = self.object.aggregate(items, *period, group_by='game__mapname', group_by_as='mapname')
        return [item for item in aggregated if item['games']]

    def get_best_game(self, field, points):
        """
        Return a Player instance with `field` equal to `points`.
        """
        try:
            assert points > 0
            period = models.Rank.get_period_for_year(self.year)
            player = (
                self.object.qualified(*period)
                .select_related('game')
                .filter(**{field: points})[:1]
                .get()
            )
        except (AssertionError, ObjectDoesNotExist):
            return None
        else:
            return player.game

    def get_best_weapon(self, aggregated):
        """Return the weapon with most kills."""
        sorted_by_kills = sorted(aggregated.values(), key=lambda weapon: weapon['kills'], reverse=True)
        try:
            return sorted_by_kills[0]
        except IndexError:
            return None

    def get_max(self, *categories):
        "Return the max values for the K/D and S/M stats."
        return jobs.get_best_kdr(self.year)


class ProfileWeaponListView(ProfileBaseView):
    template_name = 'tracker/chapters/profile/equipment.html'

    def get_context_data(self, *args, **kwargs):
        # get a list of used weapons (ie a weapon with at least one kill or a shot)
        weapons = {
            weapon: stats for weapon, stats in self.get_weapons().items()
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
        context_data = super().get_context_data(*args, **kwargs)
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
        aggregated = self.object.aggregate_weapon_stats(
            *models.Rank.get_period_for_year(self.year),
            filters={'game__gametype__in': definitions.MODES_VERSUS}
        )
        return aggregated

    def get_favourite_loadout(self):
        self.object.fetch_popular_loadout(year=self.year)

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
        context_data = super().get_context_data(*args, **kwargs)

        maps = self.get_maps()
        equipment = self.get_favourite_equipment()
        # annotate with fav equipment
        for item in maps:
            item['loadout'] = equipment[item['mapname']] if item['mapname'] in equipment else None

        context_data.update({
            'stats': self.get_stats(),
            'maps': maps,
        })
        return context_data

    def get_maps(self):
        items = {
            # best coop score
            'score_best': (
                Max('game__coop_score')
            ),
            # average coop score
            'score_avg': (
                Avg('game__coop_score')
            ),
            # average mission time
            'time_avg': (
                Avg(
                    Case(When(game__outcome__in=definitions.COMPLETED_MISSIONS, then='game__time'))
                )
            ),
            # best mission time
            'time_best': (
                Min(
                    Case(When(game__outcome__in=definitions.COMPLETED_MISSIONS, then='game__time'))
                )
            ),
            # total number of missions completed
            'missions_completed': (
                Count(
                    Case(When(game__outcome__in=definitions.COMPLETED_MISSIONS, then='game')),
                    distinct=True
                )
            ),
            # total number of missions failed
            'missions_failed': (
                Count(
                    Case(When(game__outcome__in=definitions.FAILED_MISSIONS, then='game')),
                    distinct=True
                )
            ),
        }
        aggregated = self.object.aggregate(
            items,
            *models.Rank.get_period_for_year(self.year),
            group_by='game__mapname',
            group_by_as='mapname',
            filters={'game__gametype__in': definitions.MODES_COOP, 'dropped': False}
        )
        return [item for item in aggregated if item['time_best']]

    def get_favourite_equipment(self):
        maps = {}
        period = models.Rank.get_period_for_year(self.year)
        aggregated = (
            self.object
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
            mapname: prefetched[pk] for mapname, pk in maps.items()
        }


class ProfileRankingListView(ProfileBaseView, generic.list.MultipleObjectMixin):
    template_name = 'tracker/chapters/profile/ranking.html'

    def get_context_data(self, *args, **kwargs):
        self.object_list = self.get_ranks()
        context_data = super().get_context_data(*args, **kwargs)
        context_data.update({
            'rank_list': self.object_list,
        })
        return context_data

    def get_ranks(self):
        categories = []
        # lend board list from the Leaderboad view
        ranks = BoardListView.get_boards()
        # set defaults and acqure a list of categories
        for details in ranks.values():
            details.update({
                'points': 0,
                'position': None,
            })
            categories.append(details['id'])

        entries = (
            models.Rank.objects
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
        self.object_list = (
            self.get_games()
            .filter(date_finished__gte=start, date_finished__lte=end)
        )
        context_data = super().get_context_data(*args, **kwargs)
        return context_data


class PlayerSearchView(FilterViewMixin, generic.ListView):
    template_name = 'tracker/chapters/search/search.html'
    model = models.Alias
    paginate_by = 20
    form_class = forms.PlayerSearchForm
    form = None

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.form = self.form_class(data=request.GET or None)
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        if not self.form.is_valid():
            return qs.none()
        # search by player name
        return (
            qs
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
        context_data = super().get_context_data(*args, **kwargs)
        context_data.update({
            'form': self.form,
        })
        return context_data


class ProfileRedirectView(generic.RedirectView):
    permanent = True
    """Redirect /player/Name/ requests to the search view."""

    def get_redirect_url(self, *args, **kwargs):
        return '%s?player=%s' % (reverse('tracker:search'), kwargs.get('name', ''))
