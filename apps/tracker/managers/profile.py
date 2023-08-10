import logging
import re
from datetime import timedelta, datetime
from ipaddress import IPv4Address
from typing import Any, TYPE_CHECKING

from django.conf import settings
from django.contrib.postgres.expressions import ArraySubquery
from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q, F, OuterRef, Case, When, Expression, Count, Subquery
from django.utils import timezone

from apps.geoip.models import ISP
from apps.tracker.exceptions import NoProfileMatchError
from apps.tracker.managers.stats import get_stats_period_for_year
from apps.tracker.schema import teams_reversed
from apps.utils.misc import concat_it
from apps.utils.db.func import ArrayToString, normalized_names_search_vector

if TYPE_CHECKING:
    from apps.tracker.models import Profile, Server, Game, Alias  # noqa: F401
    from apps.tracker.managers import PlayerQuerySet


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

    return any(re.search(pattern, name, re.I) for pattern in settings.TRACKER_POPULAR_NAMES)


class ProfileQuerySet(models.QuerySet):
    def for_display_card(self) -> models.QuerySet["Profile"]:
        return self.select_related("loadout").only("loadout", "name", "team", "country")

    def played(self) -> models.QuerySet["Profile"]:
        return self.filter(first_seen_at__isnull=False, last_seen_at__isnull=False)

    def require_denorm_names(self) -> models.QuerySet["Profile"]:
        return self.filter(
            Q(alias_updated_at__isnull=False),
            Q(names_updated_at__isnull=True) | Q(alias_updated_at__gt=F("names_updated_at")),
        )

    def require_search_update(self) -> models.QuerySet["Profile"]:
        return self.filter(
            Q(names_updated_at__isnull=False),
            Q(search_updated_at__isnull=True) | Q(names_updated_at__gt=F("search_updated_at")),
        )

    def require_preference_update(self) -> models.QuerySet["Profile"]:
        """
        Fetch the profiles that require updating preferences.
        Those are profiles of the players that played past the last update.
        """
        return self.played().filter(
            Q(preferences_updated_at__isnull=True) | Q(last_seen_at__gt=F("preferences_updated_at"))
        )

    def require_stats_update(self) -> models.QuerySet["Profile"]:
        """
        Fetch profiles of the players for periodic stats update.
        """
        return self.played().filter(
            Q(stats_updated_at__isnull=True) | Q(last_seen_at__gt=F("stats_updated_at"))
        )


class ProfileManager(models.Manager):
    @classmethod
    def match(
        cls,
        *,
        recent: bool = False,
        **match_kwargs: dict[str, Any],
    ) -> "Profile":
        from apps.tracker.models import Alias  # noqa: F811

        # filter players by recentness
        if recent:
            min_date = timezone.now() - timedelta(seconds=settings.TRACKER_RECENT_TIME)
            match_kwargs["player__game__date_finished__gte"] = min_date

        alias_qs = Alias.objects.select_related("profile").filter(**match_kwargs)

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
            logger.debug("will skip name lookup for %s", name)

        # the first steps rely on the name.
        # therefore, if the name is too popular, we must skip them

        # step 1: name+ip lookup
        if can_use_name:
            steps.append({"name__iexact": name, "player__ip": ip_address})

        # step 2: name+isp lookup
        if can_use_name and isp:
            steps.append({"name__iexact": name, "isp": isp})

        # step 3: name+country lookup against the recent players
        if can_use_name and isp and isp.country:
            steps.append({"recent": True, "name__iexact": name, "isp__country": isp.country})

        # step 4: ip lookup against the recent players
        steps.append({"recent": True, "player__ip": ip_address})

        return steps

    @classmethod
    def match_smart(
        cls,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None,
    ) -> "Profile":
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
                logger.debug("no profile match with %s", match_attrs)
                continue
            else:
                logger.debug("matched profile %s (%s) with %s", profile, profile.pk, match_attrs)
                return profile

        logger.debug(
            "unable to match any profile by name=%s ip_address=%s isp=%s", name, ip_address, isp
        )

        raise NoProfileMatchError

    def match_smart_or_create(
        self,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None = None,
    ) -> tuple["Profile", bool]:
        try:
            return self.match_smart(name=name, ip_address=ip_address, isp=isp), False
        except NoProfileMatchError:
            return self.create(name=name), True

    @classmethod
    def fetch_first_preferred_game_id_for_profile(cls, profile: "Profile") -> int | None:
        from apps.tracker.models import Game, Player

        # prepare a subquery to get the most recent game ids for the player
        recent_game_ids = (
            Player.objects.using("replica")
            .select_related(None)
            .for_profile(profile)
            .order_by("-pk")
            .values_list("game_id", flat=True)
        )[: settings.TRACKER_PREFERRED_GAMES]

        # of the selected games, get the earliest
        least_game_qs = (
            Game.objects.using("replica")
            .filter(pk__in=Subquery(recent_game_ids))
            .only("pk")
            .order_by("pk")
        )[:1]

        try:
            least_recent_game = least_game_qs.get()
        except ObjectDoesNotExist:
            logger.info("least recent game is not available for %s (%s)", profile, profile.pk)
            return None

        return least_recent_game.pk

    @classmethod
    def fetch_preferred_field_for_profile(
        cls,
        profile: "Profile",
        field: str,
        count_field: str | Expression | None = None,
        least_game_id: int | None = None,
    ) -> str | int | None:
        """
        Calculate the most popular item for given player field.
        """
        from apps.tracker.models import Player

        if least_game_id is None:
            least_game_id = cls.fetch_first_preferred_game_id_for_profile(profile)

        if not least_game_id:
            return None

        queryset = (
            Player.objects.using("replica")
            .for_profile(profile)
            .filter(game_id__gte=least_game_id)
            .values(field)
            .annotate(num=Count(count_field if count_field else field))
            .order_by("-num")
        )[:1]

        try:
            aggregated = queryset.get()
            return aggregated[field]
        except ObjectDoesNotExist:
            return None

    @classmethod
    def fetch_preferred_name_for_profile(
        cls, profile: "Profile", least_game_id: int | None = None
    ) -> str | None:
        """Get the most popular name"""
        return cls.fetch_preferred_field_for_profile(
            profile, "alias__name", least_game_id=least_game_id
        )

    @classmethod
    def fetch_preferred_country_for_profile(
        cls, profile: "Profile", least_game_id: int | None = None
    ) -> str | None:
        """Get the most recent country"""
        return cls.fetch_preferred_field_for_profile(
            profile, "alias__isp__country", least_game_id=least_game_id
        )

    @classmethod
    def fetch_preferred_team_for_profile(
        cls, profile: "Profile", least_game_id: int | None = None
    ) -> str | None:
        """Get the most preferred team"""
        return cls.fetch_preferred_field_for_profile(profile, "team", least_game_id=least_game_id)

    @classmethod
    def fetch_preferred_loadout_for_profile(
        cls, profile: "Profile", least_game_id: int | None = None
    ) -> int | None:
        """Fetch the most preferred non VIP loadout"""
        return cls.fetch_preferred_field_for_profile(
            profile,
            "loadout_id",
            count_field=Case(When(vip=False, then="loadout_id")),
            least_game_id=least_game_id,
        )

    @classmethod
    def update_preferences_for_profile(cls, profile: "Profile") -> None:
        """
        Update the player's recent preferences
        such as name, team, loadout and country.
        """
        if not (least_game_id := cls.fetch_first_preferred_game_id_for_profile(profile)):
            # fmt: off
            logger.info(
                "wont update preferences for %s with name=%s team=%s country=%s loadout=%s",
                profile, profile.name, profile.team, profile.country, profile.loadout_id,
            )
            # fmt: on
            return

        # fmt: off
        logger.info(
            "updating preferences for %s since %d, name=%s team=%s country=%s loadout=%s",
            profile, least_game_id, profile.name, profile.team, profile.country, profile.loadout_id,
        )
        # fmt: on

        profile.name = cls.fetch_preferred_name_for_profile(profile, least_game_id) or profile.name
        profile.country = (
            cls.fetch_preferred_country_for_profile(profile, least_game_id) or profile.country
        )
        profile.team = cls.fetch_preferred_team_for_profile(profile, least_game_id) or profile.team
        profile.team_legacy = teams_reversed.get(profile.team)
        profile.loadout_id = (
            cls.fetch_preferred_loadout_for_profile(profile, least_game_id) or profile.loadout_id
        )
        profile.preferences_updated_at = timezone.now()

        # fmt: off
        logger.info(
            "finished updating popular for %s, name=%s team=%s country=%s loadout=%s",
            profile, profile.name, profile.team, profile.country, profile.loadout_id,
        )
        # fmt: on

        profile.save(
            update_fields=[
                "name",
                "country",
                "team",
                "team_legacy",
                "loadout_id",
                "preferences_updated_at",
            ]
        )

    @classmethod
    def update_stats_for_profile(cls, profile: "Profile") -> None:
        if profile.last_seen_at:
            cls.update_annual_stats_for_profile(profile=profile, year=profile.last_seen_at.year)
        profile.stats_updated_at = timezone.now()
        profile.save(update_fields=["stats_updated_at"])

    def update_with_game(self, game: "Game") -> None:
        update_qs = self.filter(alias__player__game=game)

        first_game_update_qs = update_qs.filter(game_first__isnull=True)
        last_game_update_qs = update_qs.filter(~Q(game_last=game.pk))

        with transaction.atomic():
            first_game_update_qs.update(game_first=game, first_seen_at=game.date_finished)
            last_game_update_qs.update(game_last=game, last_seen_at=game.date_finished)

    @classmethod
    def update_annual_stats_for_profile(cls, *, profile: "Profile", year: int) -> None:
        from apps.tracker.models import (
            PlayerStats,
            MapStats,
            GametypeStats,
            ServerStats,
            WeaponStats,
        )

        if not (period := cls._get_annual_period_for_profile(profile=profile, year=year)):
            return

        logger.info("updating annual %s stats for profile %s (%d)", year, profile, profile.pk)

        queryset = cls._get_qualified_player_queryset_for_profile(
            profile=profile, period_from=period[0], period_till=period[1]
        )

        player_stats = queryset.aggregate_player_stats()
        per_map_stats = queryset.aggregate_stats_by_map()
        per_gametype_stats = queryset.aggregate_stats_by_gametype()
        per_server_stats = queryset.aggregate_stats_by_server()
        per_weapon_stats = queryset.aggregate_stats_by_weapon()

        save_kwargs = {"profile": profile, "year": year}

        with transaction.atomic(durable=True):
            PlayerStats.objects.save_stats(player_stats, **save_kwargs)
            MapStats.objects.save_grouped_stats(per_map_stats, grouping_key="map_id", **save_kwargs)
            GametypeStats.objects.save_grouped_stats(
                per_gametype_stats, grouping_key="gametype", **save_kwargs
            )
            ServerStats.objects.save_grouped_stats(
                per_server_stats, grouping_key="server_id", **save_kwargs
            )
            WeaponStats.objects.save_grouped_stats(
                per_weapon_stats, grouping_key="weapon", **save_kwargs
            )

    @classmethod
    def update_annual_server_stats_for_profile(
        cls,
        *,
        profile: "Profile",
        server: "Server",
        year: int,
        no_savepoint: bool = False,
    ) -> None:
        from apps.tracker.models import ServerStats

        if not (period := cls._get_annual_period_for_profile(profile=profile, year=year)):
            return

        logger.info(
            "updating annual %s server stats for profile %s (%d) at server %s (%s)",
            year,
            profile,
            profile.pk,
            server,
            server.pk,
        )

        queryset = cls._get_qualified_player_queryset_for_profile(
            profile=profile, period_from=period[0], period_till=period[1]
        ).for_server(server)

        per_server_stats = queryset.aggregate_stats_by_server()

        with transaction.atomic(savepoint=not no_savepoint):
            ServerStats.objects.save_grouped_stats(
                per_server_stats,
                grouping_key="server_id",
                profile=profile,
                year=year,
            )

    @classmethod
    def _get_qualified_player_queryset_for_profile(
        cls,
        *,
        profile: "Profile",
        period_from: datetime,
        period_till: datetime,
        using: str = "replica",
    ) -> "PlayerQuerySet":
        from apps.tracker.models import Player

        return (
            Player.objects.using(using)
            .for_profile(profile)
            .with_qualified_games()
            .for_period(period_from, period_till)
        )

    @classmethod
    def _get_annual_period_for_profile(
        cls, *, profile: "Profile", year: int
    ) -> tuple[datetime, datetime] | None:
        period_from, period_till = get_stats_period_for_year(year)

        if profile.first_seen_at and period_till < profile.first_seen_at:
            logger.info(
                "year %d is not actual for profile %s (%d); first seen %s > %s",
                year,
                profile,
                profile.pk,
                profile.first_seen_at,
                period_till,
            )
            return None

        if profile.last_seen_at and period_from > profile.last_seen_at:
            logger.info(
                "year %d is not actual for profile %s (%d); last seen %s < %s",
                year,
                profile,
                profile.pk,
                profile.last_seen_at,
                period_from,
            )
            return None

        return period_from, period_till

    @classmethod
    def update_player_positions_for_year(cls, year: int) -> None:
        from apps.tracker.models import PlayerStats, GametypeStats

        logger.info("updating player positions for year %s", year)

        # global player stats
        PlayerStats.objects.rank(
            year=year, cats=["spm_ratio"], qualify={"time": settings.TRACKER_MIN_TIME}
        )
        PlayerStats.objects.rank(
            year=year, cats=["spr_ratio"], qualify={"games": settings.TRACKER_MIN_GAMES}
        )
        PlayerStats.objects.rank(
            year=year, cats=["kd_ratio"], qualify={"kills": settings.TRACKER_MIN_KILLS}
        )
        PlayerStats.objects.rank(
            year=year,
            cats=["weapon_hit_ratio", "weapon_kill_ratio"],
            qualify={"weapon_shots": settings.TRACKER_MIN_WEAPON_SHOTS},
        )
        PlayerStats.objects.rank(
            year=year,
            cats=["grenade_hit_ratio"],
            qualify={"grenade_shots": settings.TRACKER_MIN_GRENADE_SHOTS},
        )
        PlayerStats.objects.rank(
            year=year,
            exclude_cats=[
                "spm_ratio",
                "spr_ratio",
                "kd_ratio",
                "weapon_hit_ratio",
                "weapon_kill_ratio",
                "grenade_hit_ratio",
                "weapon_teamhit_ratio",
                "grenade_teamhit_ratio",
            ],
        )

        # per gametype player stats
        GametypeStats.objects.rank(
            year=year, cats=["spm_ratio"], qualify={"time": settings.TRACKER_MIN_TIME}
        )
        GametypeStats.objects.rank(
            year=year, cats=["spr_ratio"], qualify={"games": settings.TRACKER_MIN_GAMES}
        )
        GametypeStats.objects.rank(year=year, exclude_cats=["spm_ratio", "spr_ratio"])

        # per server player stats
        cls.update_per_server_positions_for_year(year)

        logger.info("finished updating player positions for year %s", year)

    @classmethod
    def update_per_server_positions_for_year(
        cls,
        year: int,
        filters: dict[str, Any] | None = None,
    ) -> None:
        from apps.tracker.models import ServerStats

        rank_kwargs = {"year": year, "filters": filters}
        ServerStats.objects.rank(
            cats=["spm_ratio"], qualify={"time": settings.TRACKER_MIN_TIME}, **rank_kwargs
        )
        ServerStats.objects.rank(
            cats=["spr_ratio"], qualify={"games": settings.TRACKER_MIN_GAMES}, **rank_kwargs
        )
        ServerStats.objects.rank(
            cats=["kd_ratio"], qualify={"kills": settings.TRACKER_MIN_KILLS}, **rank_kwargs
        )
        ServerStats.objects.rank(exclude_cats=["spm_ratio", "spr_ratio", "kd_ratio"], **rank_kwargs)

    @transaction.atomic
    def denorm_alias_names(self, *profile_ids: int) -> None:
        from apps.tracker.models import Alias  # noqa: F811

        unique_alias_names_subq = (
            Alias.objects.using("replica")
            .distinct("name")
            .filter(profile_id=OuterRef("pk"))
            .values_list("name")
        )
        profile_names = (
            self.using("replica")
            .filter(pk__in=profile_ids)
            .annotate(alias_names=ArraySubquery(unique_alias_names_subq))
            .values("pk", "alias_names")
        )
        name_per_profile = {item["pk"]: item["alias_names"] for item in profile_names}

        logger.info("updating %d profiles with denormalized alias names", len(name_per_profile))
        update_qs = self.select_related(None).filter(pk__in=name_per_profile).only("pk", "name")

        for profile in update_qs:
            alias_names = name_per_profile[profile.pk]
            uniq_alias_names = [name for name in alias_names if name != profile.name]

            logger.info(
                "updating profile %s (%d) with alias names '%s'",
                profile.name,
                profile.pk,
                concat_it(uniq_alias_names),
            )
            profile.names = uniq_alias_names

        self.bulk_update(update_qs, ["names"])
        self.filter(pk__in=name_per_profile).update(names_updated_at=timezone.now())

    @transaction.atomic
    def update_search_vector(self, *profile_ids: int) -> None:
        logger.info("updating search vector for %d profiles", len(profile_ids))

        names_concat = ArrayToString(F("names"), " ")

        vector = (
            SearchVector("name", config="simple", weight="A")
            + SearchVector(names_concat, config="simple", weight="B")
            + normalized_names_search_vector(F("name"), config="simple", weight="C")
            + normalized_names_search_vector(names_concat, config="simple", weight="C")
        )

        self.filter(pk__in=profile_ids).update(search=vector)
        self.filter(pk__in=profile_ids).update(search_updated_at=timezone.now())
