import logging
import re
from datetime import timedelta, datetime
from ipaddress import IPv4Address
from typing import Any, TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone

from apps.geoip.models import ISP
from apps.tracker.exceptions import NoProfileMatchError
from apps.tracker.managers.stats import get_stats_period_for_year

if TYPE_CHECKING:
    from apps.tracker.models import Profile, Server  # noqa
    from apps.tracker.managers import PlayerQuerySet # noqa


logger = logging.getLogger(__name__)


def is_name_popular(name: str) -> bool:
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

    def for_display_card(self) -> models.QuerySet['Profile']:
        return (self.select_related('loadout')
                .only('loadout', 'name', 'team', 'country'))

    def played(self) -> models.QuerySet['Profile']:
        return self.filter(first_seen_at__isnull=False, last_seen_at__isnull=False)

    def require_preference_update(self) -> models.QuerySet['Profile']:
        """
        Fetch the profiles that require updating preferences.
        Those are profiles of the players that played past the last update.
        """
        return self.played().filter(Q(preferences_updated_at__isnull=True) |
                                    Q(last_seen_at__gt=F('preferences_updated_at')))

    def require_stats_update(self) -> models.QuerySet['Profile']:
        """
        Fetch profiles of the players for periodic stats update.
        """
        return self.played().filter(Q(stats_updated_at__isnull=True) |
                                    Q(last_seen_at__gt=F('stats_updated_at')))


class ProfileManager(models.Manager):

    @classmethod
    def match(
        cls,
        *,
        recent: bool = False,
        **match_kwargs: dict[str, Any],
    ) -> 'Profile':
        from apps.tracker.models import Alias

        # filter players by recentness
        if recent:
            min_date = timezone.now() - timedelta(seconds=settings.TRACKER_RECENT_TIME)
            match_kwargs['player__game__date_finished__gte'] = min_date

        alias_qs = Alias.objects.select_related('profile').filter(**match_kwargs)

        try:
            # limit query in case of a lookup different from name+ip pair
            alias = alias_qs[0:1].get()
        except ObjectDoesNotExist as exc:
            raise NoProfileMatchError from exc

        return alias.profile

    @classmethod
    def _prepare_match_smart_steps(
        cls,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None,
    ) -> list[dict[str, Any]]:
        steps = []
        # skip Player, afk and the other popular names
        can_use_name = not is_name_popular(name)

        if not can_use_name:
            logger.debug('will skip name lookup for %s', name)

        # the first steps rely on the name.
        # therefore, if the name is too popular, we must skip them

        # step 1: name+ip lookup
        if can_use_name:
            steps.append({'name__iexact': name, 'player__ip': ip_address})

        # step 2: name+isp lookup
        if can_use_name and isp:
            steps.append({'name__iexact': name, 'isp': isp})

        # step 3: name+country lookup against the recent players
        if can_use_name and isp and isp.country:
            steps.append({'recent': True, 'name__iexact': name, 'isp__country': isp.country})

        # step 4: ip lookup against the recent players
        steps.append({'recent': True, 'player__ip': ip_address})

        return steps

    @classmethod
    def match_smart(
        cls,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None,
    ) -> 'Profile':
        """
        Attempt to find a profile property of a player in a sequence of steps:

            1.  do a name+ip lookup
            2   if isp is present, do a name+isp lookup
            3.  if isp is present, and it has a country, do a name+country lookup
                but only for the players that have been created recently
            4.  do an ip lookup for the players that have been created recently

        If neither of the steps return an object, raise NoProfileMatch
        """
        steps = cls._prepare_match_smart_steps(name=name, ip_address=ip_address, isp=isp)

        for match_attrs in steps:
            try:
                profile = cls.match(**match_attrs)
            except NoProfileMatchError:
                logger.debug('no profile match with %s', match_attrs)
                continue
            else:
                logger.debug('matched profile %s (%s) with %s', profile, profile.pk, match_attrs)
                return profile

        logger.debug('unable to match any profile by name=%s ip_address=%s isp=%s', name, ip_address, isp)

        raise NoProfileMatchError

    def match_smart_or_create(
        self,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None = None,
    ) -> tuple['Profile', bool]:
        try:
            return self.match_smart(name=name, ip_address=ip_address, isp=isp), False
        except NoProfileMatchError:
            return self.create(name=name), True

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
