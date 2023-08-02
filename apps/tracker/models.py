import logging
from typing import ClassVar

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.core.cache import cache
from django.db import models
from django.db.models import Q, F, When, Case, Count, Func, Expression, Subquery
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.functions import Upper
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from apps.tracker.entities import GameType, Equipment, GameNeighbors
from apps.tracker.managers import (
    ServerQuerySet,
    ServerManager,
    MapManager,
    GameManager,
    LoadoutManager,
    AliasManager,
    PlayerManager,
    PlayerQuerySet,
    ProfileManager,
    ProfileQuerySet,
    StatsManager,
    ServerStatsManager,
)
from apps.tracker.managers.alias import AliasQuerySet
from apps.tracker.schema import teams_reversed
from apps.tracker.utils.game import map_background_picture
from apps.tracker.utils.misc import force_clean_name, ratio
from apps.utils.db.fields import EnumField
from apps.utils.misc import dumps

logger = logging.getLogger(__name__)


class Server(models.Model):
    ip = models.GenericIPAddressField(protocol="IPv4")
    port = models.PositiveIntegerField()
    status_port = models.PositiveIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    listed = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    country = models.CharField(max_length=2, null=True, blank=True)
    hostname = models.CharField(max_length=256, null=True, blank=True)
    version = models.CharField(max_length=64, null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=0)

    merged_into = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    merged_into_at = models.DateTimeField(null=True, blank=True)
    merged_stats_at = models.DateTimeField(null=True, blank=True)

    # pending removal
    port_gs1 = models.PositiveIntegerField(null=True, blank=True)
    port_gs2 = models.PositiveIntegerField(null=True, blank=True)
    streamed = models.BooleanField(default=False)

    objects = ServerManager.from_queryset(ServerQuerySet)()

    class Meta:
        unique_together = (("ip", "port"),)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                Func(F("ip"), function="host"), F("port"), name="tracker_server_host_ip_port"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        self.clean()
        # set default status port
        if not self.status_port:
            self.status_port = self.port + 1
        super().save(*args, **kwargs)

    @cached_property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"

    @cached_property
    def name(self) -> str:
        if self.hostname:
            return force_clean_name(self.hostname)
        return self.address

    def clean(self) -> None:
        """
        Ensure port is in valid range.

        :raises django.core.exceptions.ValidationError: If port is invalid
        """
        try:
            self.port = int(self.port)
            if not (1 <= self.port <= 65535):
                raise AssertionError
        except (ValueError, AssertionError):
            raise ValidationError(_("Port number must be between 1 and 65535 inclusive."))

    def update_with_status(self, status: dict[str, str | list[dict[str, str]]]) -> None:
        redis = cache.client.get_client()
        logger.info("storing status for server %s:%s (%s)", self.ip, self.port, self.pk)
        redis.hset(settings.TRACKER_STATUS_REDIS_KEY, self.address, dumps(status).encode())


class Map(models.Model):
    name = models.CharField(max_length=255, unique=True)

    objects = MapManager()

    def __str__(self) -> str:
        return self.name

    @cached_property
    def slug(self):
        return slugify(self.name)

    @cached_property
    def preview_picture(self):
        return map_background_picture(self.name, style="preview")

    @cached_property
    def background_picture(self):
        return map_background_picture(self.name, style="background")


class Game(models.Model):
    server = models.ForeignKey("Server", on_delete=models.PROTECT)
    tag = models.CharField(max_length=8, null=True, unique=True)
    time = models.SmallIntegerField(default=0)
    outcome = EnumField(db_column="outcome_enum", enum_type="outcome_enum", null=True)
    outcome_legacy = models.SmallIntegerField(db_column="outcome", default=0)
    gametype = EnumField(db_column="gametype_enum", enum_type="gametype_enum")
    gametype_legacy = models.SmallIntegerField(db_column="gametype")
    map = models.ForeignKey("Map", on_delete=models.PROTECT)  # noqa: A003
    player_num = models.SmallIntegerField(default=0)
    score_swat = models.SmallIntegerField(default=0)
    score_sus = models.SmallIntegerField(default=0)
    vict_swat = models.SmallIntegerField(default=0)
    vict_sus = models.SmallIntegerField(default=0)
    rd_bombs_defused = models.SmallIntegerField(default=0)
    rd_bombs_total = models.SmallIntegerField(default=0)
    coop_score = models.SmallIntegerField(default=0)
    date_finished = models.DateTimeField(default=timezone.now)

    # pending removal
    mapname = models.SmallIntegerField()

    objects = GameManager()

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                (F("score_swat") + F("score_sus")).desc(), name="tracker_game_score_swat_score_sus"
            ),
            models.Index(F("date_finished").desc(), name="tracker_game_date_finished_desc"),
        ]

    def __str__(self) -> str:
        return f"{self.date_finished} - {self.time} - {self.outcome}"

    @cached_property
    def is_coop_game(self):
        return self.gametype in (GameType.co_op, GameType.co_op_qmm)

    def get_neighboring_games(self) -> GameNeighbors:
        return Game.objects.get_neighbors_for_game(self)


class Loadout(models.Model):
    primary = EnumField(db_column="primary_enum", enum_type="equipment_enum")
    primary_legacy = models.SmallIntegerField(db_column="primary", default=0)

    primary_ammo = EnumField(db_column="primary_ammo_enum", enum_type="ammo_enum")
    primary_ammo_legacy = models.SmallIntegerField(db_column="primary_ammo", default=0)

    secondary = EnumField(db_column="secondary_enum", enum_type="equipment_enum")
    secondary_legacy = models.SmallIntegerField(db_column="secondary", default=0)

    secondary_ammo = EnumField(db_column="secondary_ammo_enum", enum_type="ammo_enum")
    secondary_ammo_legacy = models.SmallIntegerField(db_column="secondary_ammo", default=0)

    equip_one = EnumField(db_column="equip_one_enum", enum_type="equipment_enum")
    equip_one_legacy = models.SmallIntegerField(db_column="equip_one", default=0)

    equip_two = EnumField(db_column="equip_two_enum", enum_type="equipment_enum")
    equip_two_legacy = models.SmallIntegerField(db_column="equip_two", default=0)

    equip_three = EnumField(db_column="equip_three_enum", enum_type="equipment_enum")
    equip_three_legacy = models.SmallIntegerField(db_column="equip_three", default=0)

    equip_four = EnumField(db_column="equip_four_enum", enum_type="equipment_enum")
    equip_four_legacy = models.SmallIntegerField(db_column="equip_four", default=0)

    equip_five = EnumField(db_column="equip_five_enum", enum_type="equipment_enum")
    equip_five_legacy = models.SmallIntegerField(db_column="equip_five", default=0)

    breacher = EnumField(db_column="breacher_enum", enum_type="equipment_enum")
    breacher_legacy = models.SmallIntegerField(db_column="breacher", default=0)

    head = EnumField(db_column="head_enum", enum_type="equipment_enum")
    head_legacy = models.SmallIntegerField(db_column="head", default=0)

    body = EnumField(db_column="body_enum", enum_type="equipment_enum")
    body_legacy = models.SmallIntegerField(db_column="body", default=0)

    objects = LoadoutManager()

    class Meta:
        unique_together = (
            (
                "primary",
                "secondary",
                "primary_ammo",
                "secondary_ammo",
                "equip_one",
                "equip_two",
                "equip_three",
                "equip_four",
                "equip_five",
                "head",
                "body",
                "breacher",
            ),
        )

    def __str__(self) -> str:
        return f"{self.primary} - {self.secondary} - {self.head} - {self.body} ({self.pk})"


class Weapon(models.Model):
    id = models.BigAutoField("ID", primary_key=True)  # noqa: A003
    player = models.ForeignKey(
        "Player", on_delete=models.CASCADE, related_name="weapons", related_query_name="weapon"
    )
    name = EnumField(db_column="name_enum", enum_type="equipment_enum")
    name_legacy = models.SmallIntegerField(db_column="name")
    time = models.SmallIntegerField(default=0)
    shots = models.SmallIntegerField(default=0)
    hits = models.SmallIntegerField(default=0)
    teamhits = models.SmallIntegerField(default=0)
    kills = models.SmallIntegerField(default=0)
    teamkills = models.SmallIntegerField(default=0)
    distance = models.FloatField(_("Distance, meters"), default=0)

    _grenade_weapons: ClassVar[set[str]] = set(Equipment.grenades())

    def __str__(self) -> str:
        return f"{self.name} of player {self.player_id} ({self.pk})"

    @cached_property
    def is_grenade_weapon(self):
        return self.name in self._grenade_weapons

    @cached_property
    def accuracy(self):
        min_shots = (
            settings.TRACKER_MIN_GAME_GRENADES
            if self.is_grenade_weapon
            else settings.TRACKER_MIN_GAME_AMMO
        )
        return int(ratio(self.hits, self.shots, min_divisor=min_shots) * 100)


class Alias(models.Model):
    name = models.CharField(max_length=64)
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE)
    isp = models.ForeignKey("geoip.ISP", related_name="+", null=True, on_delete=models.PROTECT)

    search = SearchVectorField(
        null=True, help_text=_("TSV field for full text search. Updated by triggers.")
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = AliasManager.from_queryset(AliasQuerySet)()

    class Meta:
        index_together = (("name", "isp"),)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(Upper("name"), F("isp_id"), name="tracker_alias_upper_name_isp_id"),
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.isp}"


class Player(models.Model):
    game = models.ForeignKey("Game", on_delete=models.PROTECT)
    alias = models.ForeignKey("Alias", on_delete=models.PROTECT)
    loadout = models.ForeignKey("Loadout", on_delete=models.PROTECT)
    ip = models.GenericIPAddressField(protocol="IPv4")

    team = EnumField(db_column="team_enum", enum_type="team_enum")
    team_legacy = models.SmallIntegerField(db_column="team")
    coop_status = EnumField(db_column="coop_status_enum", enum_type="coop_status_enum", null=True)
    coop_status_legacy = models.SmallIntegerField(db_column="coop_status", default=0)
    vip = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    dropped = models.BooleanField(default=False)

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

    objects = PlayerManager.from_queryset(PlayerQuerySet)()

    _gun_weapon_names: ClassVar[set[str]] = set(
        Equipment.primary_weapons() + Equipment.secondary_weapons()
    )
    _grenade_weapon_names: ClassVar[set[str]] = set(Equipment.grenades())

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                Func(F("ip"), function="host"),
                F("id").desc(),
                name="tracker_player_host_ip_id_desc",
            ),
        ]
        index_together = (
            ("alias", "score"),
            ("alias", "kills"),
            ("alias", "arrests"),
            ("alias", "kill_streak"),
            ("alias", "arrest_streak"),
        )

    def __str__(self) -> str:
        return f"{self.name}, {self.ip}"

    @cached_property
    def profile(self):
        return self.alias.profile

    @cached_property
    def name(self):
        return self.alias.name

    @cached_property
    def country(self):
        try:
            return self.alias.isp.country
        except AttributeError:
            return None

    @cached_property
    def special(self):
        return (
            self.vip_escapes
            + self.vip_captures
            + self.vip_rescues
            + self.rd_bombs_defused
            + self.sg_escapes
        )

    @cached_property
    def coop_enemy_incaps_and_kills(self):
        return self.coop_enemy_incaps + self.coop_enemy_kills

    @cached_property
    def gun_weapons(self) -> list[Weapon]:
        return [weapon for weapon in self.weapons.all() if weapon.name in self._gun_weapon_names]

    @cached_property
    def gun_weapon_shots(self):
        """
        Calculate the number of rounds fired for both primary and secondary weapons.
        """
        shots = 0
        for weapon in self.weapons.all():
            if weapon.name not in self._gun_weapon_names:
                continue
            shots += weapon.shots
        return shots

    @cached_property
    def gun_weapon_accuracy(self) -> int:
        """
        Calculate the average accuracy for all fired weapons,
        excluding some nonlegit weapons such as taser.
        """
        return self._calculate_accuracy(
            weapon_names=self._gun_weapon_names, min_shots=settings.TRACKER_MIN_GAME_AMMO
        )

    @cached_property
    def grenade_accuracy(self) -> int:
        ratio = self._calculate_accuracy(
            weapon_names=self._grenade_weapon_names, min_shots=settings.TRACKER_MIN_GAME_GRENADES
        )
        return min(ratio, 100)

    def _calculate_accuracy(self, *, weapon_names: set, min_shots: int) -> int:
        hits = 0
        shots = 0
        for weapon in self.weapons.all():
            if weapon.name not in weapon_names:
                continue
            hits += weapon.hits
            shots += weapon.shots
        return int(ratio(hits, shots, min_divisor=min_shots) * 100)


class Objective(models.Model):
    id = models.BigAutoField("ID", primary_key=True)  # noqa: A003
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    name = EnumField(db_column="name_enum", enum_type="objective_enum")
    name_legacy = models.SmallIntegerField(db_column="name")
    status = EnumField(db_column="status_enum", enum_type="objective_status_enum")
    status_legacy = models.SmallIntegerField(db_column="status", default=0)

    class Meta:
        pass

    def __str__(self) -> str:
        return f"{self.name}, {self.status}"


class Procedure(models.Model):
    id = models.BigAutoField("ID", primary_key=True)  # noqa: A003
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    name = EnumField(db_column="name_enum", enum_type="procedure_enum")
    name_legacy = models.SmallIntegerField(db_column="name")
    status = models.CharField(max_length=7)
    score = models.SmallIntegerField(default=0)

    class Meta:
        pass

    def __str__(self) -> str:
        return f"{self.name}, {self.score} ({self.status})"


class Profile(models.Model):
    name = models.CharField(max_length=64, null=True)
    team = EnumField(db_column="team_enum", enum_type="team_enum", null=True)
    team_legacy = models.SmallIntegerField(db_column="team", null=True)
    country = models.CharField(max_length=2, null=True)
    loadout = models.ForeignKey("Loadout", null=True, on_delete=models.PROTECT)
    game_first = models.ForeignKey("Game", related_name="+", null=True, on_delete=models.PROTECT)
    game_last = models.ForeignKey("Game", related_name="+", null=True, on_delete=models.PROTECT)
    first_seen_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    stats_updated_at = models.DateTimeField(null=True)
    preferences_updated_at = models.DateTimeField(null=True)

    names = ArrayField(
        models.TextField(),
        null=True,
        help_text=_("Denormalized list of alias names for search vector. Updated by triggers."),
    )
    search = SearchVectorField(
        null=True, help_text=_("TSV field for full text search. Updated by triggers.")
    )

    objects = ProfileManager.from_queryset(ProfileQuerySet)()

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                Upper("country"),
                F("last_seen_at").desc(),
                F("id"),
                condition=Q(last_seen_at__isnull=False),
                name="tracker_profile_search_by_country_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.country}"

    def fetch_first_preferred_game_id(self) -> int | None:
        # prepare a subquery to get the most recent game ids for the player
        recent_game_ids = (
            Player.objects.using("replica")
            .select_related(None)
            .for_profile(self)
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
            logger.info("least recent game is not available for %s (%s)", self, self.pk)
            return None

        return least_recent_game.pk

    def fetch_preferred_field(
        self,
        field: str,
        count_field: str | Expression | None = None,
        least_game_id: int | None = None,
    ) -> str | int | None:
        """
        Calculate the most popular item for given player field.
        """
        if least_game_id is None:
            least_game_id = self.fetch_first_preferred_game_id()

        if not least_game_id:
            return None

        queryset = (
            Player.objects.using("replica")
            .for_profile(self)
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

    def fetch_preferred_name(self, least_game_id: int | None = None) -> str | None:
        """Get the most popular name"""
        return self.fetch_preferred_field("alias__name", least_game_id=least_game_id)

    def fetch_preferred_country(self, least_game_id: int | None = None) -> str | None:
        """Get the most recent country"""
        return self.fetch_preferred_field("alias__isp__country", least_game_id=least_game_id)

    def fetch_preferred_team(self, least_game_id: int | None = None) -> str | None:
        """Get the most preferred team"""
        return self.fetch_preferred_field("team", least_game_id=least_game_id)

    def fetch_preferred_loadout(self, least_game_id: int | None = None) -> int | None:
        """Fetch the most preferred non VIP loadout"""
        return self.fetch_preferred_field(
            "loadout_id",
            count_field=Case(When(vip=False, then="loadout_id")),
            least_game_id=least_game_id,
        )

    def update_preferences(self):
        """
        Update the player's recent preferences
        such as name, team, loadout and country.
        """
        if not (least_game_id := self.fetch_first_preferred_game_id()):
            logger.info(
                "wont update preferences for %s with name=%s team=%s country=%s loadout=%s",
                self,
                self.name,
                self.team,
                self.country,
                self.loadout_id,
            )
            return

        logger.info(
            "updating preferences for %s since %d, name=%s team=%s country=%s loadout=%s",
            self,
            least_game_id,
            self.name,
            self.team,
            self.country,
            self.loadout_id,
        )

        self.name = self.fetch_preferred_name(least_game_id) or self.name
        self.country = self.fetch_preferred_country(least_game_id) or self.country
        self.team = self.fetch_preferred_team(least_game_id) or self.team
        self.team_legacy = teams_reversed.get(self.team)
        self.loadout_id = self.fetch_preferred_loadout(least_game_id) or self.loadout_id
        self.preferences_updated_at = timezone.now()

        logger.info(
            "finished updating popular for %s, name=%s team=%s country=%s loadout=%s",
            self,
            self.name,
            self.team,
            self.country,
            self.loadout_id,
        )

        self.save(
            update_fields=[
                "name",
                "country",
                "team",
                "team_legacy",
                "loadout_id",
                "preferences_updated_at",
            ]
        )


class Stats(models.Model):
    category = EnumField(enum_type="stats_category_enum")
    year = models.SmallIntegerField()
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE)
    points = models.FloatField(default=0)
    position = models.PositiveIntegerField(null=True, db_index=True)

    objects = StatsManager()

    class Meta:
        abstract = True


class PlayerStats(Stats):
    # FIXME: set not null
    category = EnumField(db_column="category_enum", enum_type="stats_category_enum", null=True)
    category_legacy = models.SmallIntegerField(db_column="category")

    class Meta:
        db_table = "tracker_rank"
        unique_together = (
            "year",
            "category_legacy",
            "profile",
        )
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                "year",
                "category_legacy",
                condition=Q(position__lte=5),
                name="tracker_rank_year_category_position_lte",
            ),
        ]

    grouping_fields: ClassVar[list[str]] = ["category_legacy"]
    unique_db_fields: ClassVar[list[str]] = ["year", "category_legacy", "profile_id"]


class MapStats(Stats):
    map = models.ForeignKey("Map", on_delete=models.CASCADE)  # noqa: A003

    class Meta:
        unique_together = (
            "year",
            "category",
            "profile",
            "map",
        )

    grouping_fields: ClassVar[list[str]] = ["category", "map_id"]
    unique_db_fields: ClassVar[list[str]] = ["year", "category", "profile_id", "map_id"]


class GametypeStats(Stats):
    gametype = EnumField(enum_type="gametype_enum")

    class Meta:
        unique_together = (
            "year",
            "category",
            "profile",
            "gametype",
        )

    grouping_fields: ClassVar[list[str]] = ["category", "gametype"]
    unique_db_fields: ClassVar[list[str]] = ["year", "category", "profile_id", "gametype"]


class ServerStats(Stats):
    server = models.ForeignKey("Server", on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            "year",
            "category",
            "profile",
            "server",
        )

    objects = ServerStatsManager()

    grouping_fields: ClassVar[list[str]] = ["category", "server_id"]
    unique_db_fields: ClassVar[list[str]] = ["year", "category", "profile_id", "server_id"]


class WeaponStats(Stats):
    weapon = EnumField(enum_type="equipment_enum")

    class Meta:
        unique_together = (
            "year",
            "category",
            "profile",
            "weapon",
        )

    grouping_fields: ClassVar[list[str]] = ["category", "weapon"]
    unique_db_fields: ClassVar[list[str]] = ["year", "category", "profile_id", "weapon"]
