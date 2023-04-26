import logging
import re
from datetime import timedelta, datetime
from typing import Any, TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone

from apps.geoip.models import ISP
from apps.tracker.managers.stats import get_stats_period_for_year

if TYPE_CHECKING:
    from apps.tracker.models import Profile, Server  # noqa
    from apps.tracker.managers import PlayerQuerySet # noqa


logger = logging.getLogger(__name__)


def is_name_popular(name):
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


class ProfileQuerySet(models.QuerySet):

    def for_display_card(self):
        return (self.select_related('loadout')
                .only('loadout', 'name', 'team', 'country'))

    def played(self):
        return self.filter(first_seen_at__isnull=False, last_seen_at__isnull=False)

    def require_preference_update(self):
        """
        Fetch the profiles that require updating preferences.
        Those are profiles of the players that played past the last update.
        """
        return self.played().filter(Q(preferences_updated_at__isnull=True) |
                                    Q(last_seen_at__gt=F('preferences_updated_at')))

    def require_stats_update(self):
        """
        Fetch profiles of the players for periodic stats update.
        """
        return self.played().filter(Q(stats_updated_at__isnull=True) |
                                    Q(last_seen_at__gt=F('stats_updated_at')))


class ProfileManager(models.Manager):

    @classmethod
    def match(cls, **kwargs):
        from apps.tracker.models import Alias

        recent = kwargs.pop('recent', False)
        queryset = kwargs.pop('queryset', Alias.objects.all())
        # filter by min played date
        if recent:
            min_date = timezone.now() - timedelta(seconds=settings.TRACKER_RECENT_TIME)
            kwargs['player__game__date_finished__gte'] = min_date

        # limit query in case of a lookup different from name+ip pair
        return queryset.select_related('profile').filter(**kwargs)[0:1].get().profile

    @classmethod
    def match_recent(cls, **kwargs):
        return cls.match(recent=True, **kwargs)

    @classmethod
    def _prepare_match_smart_steps(cls, **kwargs: Any) -> list[tuple[callable, dict[str, Any]]]:
        steps = []
        # skip Player, afk and the other popular names
        skip_name = 'name' in kwargs and is_name_popular(kwargs['name'])

        if skip_name:
            logger.debug('will skip name lookup for %s', kwargs['name'])

        if 'ip' in kwargs:
            if 'name' in kwargs:
                # match a player with a case-insensitive lookup unless the name is way too popular
                if not skip_name:
                    steps.append((cls.match, {'name__iexact': kwargs['name'], 'player__ip': kwargs['ip']}))
            # isp may as well be None
            # in that case we should not perform a lookup
            if 'isp' not in kwargs:
                kwargs['isp'] = ISP.objects.match_or_create(kwargs['ip'])[0]

        # isp must not be None for a name+isp lookup
        if 'name' in kwargs and (not skip_name) and kwargs.get('isp'):
            # search for a player by case-insensitive name and non-None isp
            steps.append((cls.match, {'name__iexact': kwargs['name'], 'isp': kwargs['isp']}))
            # search by name+non-empty country
            if kwargs['isp'].country:
                steps.append((cls.match_recent,
                              {'name__iexact': kwargs['name'], 'isp__country': kwargs['isp'].country}))

        if 'ip' in kwargs:
            # search for a player who has recently played with the same ip
            steps.append((cls.match_recent, {'player__ip': kwargs['ip']}))

        return steps

    @classmethod
    def match_smart(cls, **kwargs):
        """
        Attempt to find a profile property of a player in a sequence of steps:

            1.  if `name` and `ip` are provided, perform a `name`+`ip`
                case-insensitive lookup.
            2   if `name` and `isp` are provided and the `isp` is not None, perform a
                `name`+`isp` case-insensitive lookup
            3.  As an extra step also perform a case-sensitive lookup for a recently
                created name+non-empty country Player entry.
            4.  if `ip` is provided, perform an ip lookup against related Player entries
                that have been created right now or `Profile.TIME_RECENT` seconds earlier.

        In case neither of the steps return an object, raise a Profile.DoesNotExist exception
        """
        steps = cls._prepare_match_smart_steps(**kwargs)

        for method, attrs in steps:
            try:
                obj = method(**attrs)
            except ObjectDoesNotExist:
                logger.debug('no profile match with %s by %s', method.__name__, attrs)
                continue
            else:
                logger.debug('matched profile %s with %s by %s', obj, method.__name__, attrs)
                return obj

        logger.debug('unable to match any profile by %s', kwargs)
        raise ObjectDoesNotExist

    def match_smart_or_create(self, **kwargs: Any) -> tuple['Profile', bool]:
        try:
            return self.match_smart(**kwargs), False
        except ObjectDoesNotExist:
            return super().create(name=kwargs.get('name')), True

    @classmethod
    def update_stats_for_profile(cls, profile: 'Profile') -> None:
        if profile.last_seen_at:
            cls.update_annual_stats_for_profile(profile=profile, year=profile.last_seen_at.year)
        profile.stats_updated_at = timezone.now()
        profile.save(update_fields=['stats_updated_at'])

    @classmethod
    def update_annual_stats_for_profile(cls, *, profile: 'Profile', year: int) -> None:
        from apps.tracker.models import PlayerStats, MapStats, GametypeStats, ServerStats, WeaponStats

        if not (period := cls._get_annual_period_for_profile(profile=profile, year=year)):
            return

        logger.info('updating annual %s stats for profile %s (%d)', year, profile, profile.pk)

        queryset = cls._get_qualified_player_queryset_for_profile(profile=profile,
                                                                  period_from=period[0], period_till=period[1])

        player_stats = queryset.aggregate_player_stats()
        per_map_stats = queryset.aggregate_stats_by_map()
        per_gametype_stats = queryset.aggregate_stats_by_gametype()
        per_server_stats = queryset.aggregate_stats_by_server()
        per_weapon_stats = queryset.aggregate_stats_by_weapon()

        save_kwargs = {'profile': profile, 'year': year}

        with transaction.atomic(durable=True):
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
    def update_annual_server_stats_for_profile(
        cls,
        *,
        profile: 'Profile',
        server: 'Server',
        year: int,
        no_savepoint: bool = False,
    ) -> None:
        from apps.tracker.models import ServerStats

        if not (period := cls._get_annual_period_for_profile(profile=profile, year=year)):
            return

        logger.info('updating annual %s server stats for profile %s (%d) at server %s (%s)',
                    year, profile, profile.pk, server, server.pk)

        queryset = (
            cls
            ._get_qualified_player_queryset_for_profile(profile=profile,
                                                        period_from=period[0],
                                                        period_till=period[1])
            .for_server(server)
        )

        per_server_stats = queryset.aggregate_stats_by_server()

        with transaction.atomic(savepoint=not no_savepoint):
            ServerStats.objects.save_grouped_stats(
                per_server_stats,
                grouping_key='server_id',
                profile=profile,
                year=year,
            )

    @classmethod
    def _get_qualified_player_queryset_for_profile(
        cls,
        *,
        profile: 'Profile',
        period_from: datetime,
        period_till: datetime,
        using: str = 'replica',
    ) -> 'PlayerQuerySet':
        from apps.tracker.models import Player
        return (
            Player.objects.using(using)
            .for_profile(profile)
            .with_qualified_games()
            .for_period(period_from, period_till)
        )

    @classmethod
    def _get_annual_period_for_profile(cls, *, profile: 'Profile', year: int) -> tuple[datetime, datetime] | None:
        period_from, period_till = get_stats_period_for_year(year)

        if profile.first_seen_at and period_till < profile.first_seen_at:
            logger.info('year %d is not actual for profile %s (%d); first seen %s > %s',
                        year, profile, profile.pk, profile.first_seen_at, period_till)
            return None

        if profile.last_seen_at and period_from > profile.last_seen_at:
            logger.info('year %d is not actual for profile %s (%d); last seen %s < %s',
                        year, profile, profile.pk, profile.last_seen_at, period_from)
            return None

        return period_from, period_till

    @classmethod
    def update_player_positions_for_year(cls, year: int) -> None:
        from apps.tracker.models import PlayerStats, GametypeStats

        logger.info('updating player positions for year %s', year)

        # global player stats
        PlayerStats.objects.rank(year=year, cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME})
        PlayerStats.objects.rank(year=year, cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES})
        PlayerStats.objects.rank(year=year, cats=['kd_ratio'], qualify={'kills': settings.TRACKER_MIN_KILLS})
        PlayerStats.objects.rank(year=year,
                                 cats=['weapon_hit_ratio', 'weapon_kill_ratio'],
                                 qualify={'weapon_shots': settings.TRACKER_MIN_WEAPON_SHOTS})
        PlayerStats.objects.rank(year=year,
                                 cats=['grenade_hit_ratio'],
                                 qualify={'grenade_shots': settings.TRACKER_MIN_GRENADE_SHOTS})
        PlayerStats.objects.rank(year=year,
                                 exclude_cats=['spm_ratio', 'spr_ratio', 'kd_ratio',
                                               'weapon_hit_ratio', 'weapon_kill_ratio', 'grenade_hit_ratio',
                                               'weapon_teamhit_ratio', 'grenade_teamhit_ratio'])

        # per gametype player stats
        GametypeStats.objects.rank(year=year, cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME})
        GametypeStats.objects.rank(year=year, cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES})
        GametypeStats.objects.rank(year=year, exclude_cats=['spm_ratio', 'spr_ratio'])

        # per server player stats
        cls.update_per_server_positions_for_year(year)

        logger.info('finished updating player positions for year %s', year)

    @classmethod
    def update_per_server_positions_for_year(
        cls,
        year: int,
        filters: dict[str, Any] = None,
    ) -> None:
        from apps.tracker.models import ServerStats
        rank_kwargs = {'year': year, 'filters': filters}
        ServerStats.objects.rank(cats=['spm_ratio'], qualify={'time': settings.TRACKER_MIN_TIME}, **rank_kwargs)
        ServerStats.objects.rank(cats=['spr_ratio'], qualify={'games': settings.TRACKER_MIN_GAMES}, **rank_kwargs)
        ServerStats.objects.rank(cats=['kd_ratio'], qualify={'kills': settings.TRACKER_MIN_KILLS}, **rank_kwargs)
        ServerStats.objects.rank(exclude_cats=['spm_ratio', 'spr_ratio', 'kd_ratio'], **rank_kwargs)
