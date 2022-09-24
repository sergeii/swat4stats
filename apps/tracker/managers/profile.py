import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

from apps.geoip.models import ISP


logger = logging.getLogger(__name__)


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

    def match(self, **kwargs):
        from apps.tracker.models import Alias

        recent = kwargs.pop('recent', False)
        queryset = kwargs.pop('queryset', Alias.objects.all())
        # filter by min played date
        if recent:
            min_date = timezone.now() - timedelta(seconds=settings.TRACKER_RECENT_TIME)
            kwargs['player__game__date_finished__gte'] = min_date

        # limit query in case of a lookup different from name+ip pair
        return queryset.select_related('profile').filter(**kwargs)[0:1].get().profile

    def match_recent(self, **kwargs):
        return self.match(recent=True, **kwargs)

    def _prepare_match_smart_steps(self, **kwargs: Any) -> list[tuple[callable, dict[str, Any]]]:
        steps = []
        # skip Player, afk and the other popular names
        skip_name = 'name' in kwargs and self.model.is_name_popular(kwargs['name'])

        if skip_name:
            logger.debug('will skip name lookup for %s', kwargs['name'])

        if 'ip' in kwargs:
            if 'name' in kwargs:
                # match a player with a case-insensitive lookup unless the name is way too popular
                if not skip_name:
                    steps.append((self.match, {'name__iexact': kwargs['name'], 'player__ip': kwargs['ip']}))
            # isp may as well be None
            # in that case we should not perform a lookup
            if 'isp' not in kwargs:
                kwargs['isp'] = ISP.objects.match_or_create(kwargs['ip'])[0]

        # isp must not be None for a name+isp lookup
        if 'name' in kwargs and (not skip_name) and kwargs.get('isp'):
            # search for a player by case-insensitive name and non-None isp
            steps.append((self.match, {'name__iexact': kwargs['name'], 'isp': kwargs['isp']}))
            # search by name+non-empty country
            if kwargs['isp'].country:
                steps.append((self.match_recent,
                              {'name__iexact': kwargs['name'], 'isp__country': kwargs['isp'].country}))

        if 'ip' in kwargs:
            # search for a player who has recently played with the same ip
            steps.append((self.match_recent, {'player__ip': kwargs['ip']}))

        return steps

    def match_smart(self, **kwargs):
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
        steps = self._prepare_match_smart_steps(**kwargs)

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
        raise self.model.DoesNotExist

    def match_smart_or_create(self, **kwargs):
        try:
            return self.match_smart(**kwargs), False
        except ObjectDoesNotExist:
            return super().get_queryset().create(name=kwargs.get('name')), True
