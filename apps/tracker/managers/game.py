import logging
import math
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import IntegrityError, models, transaction
from django.utils.translation import gettext_lazy as _

from apps.tracker.entities import (
    CoopRank,
    GameNeighbors,
    GamePlayerHighlight,
    GameTopFieldPlayer,
    GameType,
)
from apps.tracker.exceptions import GameAlreadySavedError
from apps.tracker.schema import (
    coop_status_reversed,
    gametypes_reversed,
    mapnames_reversed,
    objective_status_reversed,
    objectives_reversed,
    outcome_reversed,
    procedures_reversed,
    teams_reversed,
    weapon_reversed,
)
from apps.tracker.utils.misc import force_name

if TYPE_CHECKING:
    from apps.tracker.models import Game, Player, Server  # noqa: F401


logger = logging.getLogger(__name__)


class GameManager(models.Manager):
    highlights: ClassVar[list[str, str]] = [
        (_("Hostage Crisis"), _("%(points)s VIP rescues"), "vip_rescues", 2),
        (_("No Exit"), _("%(points)s VIP captures"), "vip_captures", 2),
        (_("Quick Cut"), _("%(points)s bombs defused"), "rd_bombs_defused", 2),
        (_("Undying"), _("%(points)s enemies killed in a row"), "kill_streak", 5),
        (_("Insane"), _("%(points)s enemies arrested in a row"), "arrest_streak", 5),
        (_("Top Gun"), _("%(points)s points earned"), "score", 30),
        (
            _("Fire in the hole!"),
            _("%(points)s%% of grenades hit their targets"),
            "grenade_accuracy",
            50,
        ),
        (_("Sharpshooter"), _("%(points)s%% of all shots hit targets"), "gun_weapon_accuracy", 25),
        (_("Killing Machine"), _("%(points)s enemies eliminated"), "kills", 10),
        (_("Resourceful"), _("%(points)s rounds of ammo fired"), "gun_weapon_shots", 300),
        # COOP
        (_("Entry team to TOC!"), _("%(points)s reports sent to TOC"), "coop_toc_reports", 10),
        (_("Hostage Crisis"), _("%(points)s civilians rescued"), "coop_hostage_arrests", 5),
        (_("The pacifist"), _("%(points)s suspects secured"), "coop_enemy_arrests", 5),
        (_("No Mercy"), _("%(points)s suspects neutralized"), "coop_enemy_incaps_and_kills", 5),
    ]
    highlights_weapon_min_kills = 5
    highlights_weapon_min_accuracy = 20

    coop_min_score_for_rank: ClassVar[list[tuple[int, CoopRank]]] = [
        (100, CoopRank.chief_inspector),
        (95, CoopRank.inspector),
        (90, CoopRank.captain),
        (85, CoopRank.lieutenant),
        (80, CoopRank.sergeant),
        (75, CoopRank.patrol_officer),
        (70, CoopRank.reserve_officer),
        (60, CoopRank.non_sworn_officer),
        (50, CoopRank.recruit),
        (35, CoopRank.washout),
        (20, CoopRank.vigilante),
        (-math.inf, CoopRank.menace),
    ]

    @transaction.atomic
    def create_game(
        self,
        server: "Server",
        data: dict[str, Any],
        date_finished: datetime,
    ) -> "Game":
        """
        Attempt to create using data that was received from a game server.

        :param server: Server the data was received from
        :param data: Validated game data
        :param date_finished: Date the data was received
        :return: Created game instance
        """
        from apps.tracker.models import Map

        gametype = GameType(data["gametype"])
        coop_procedures = data.get("coop_procedures")

        if gametype.is_coop():
            coop_score = self._calculate_coop_score_for_procedures(coop_procedures)
            coop_rank = self.calculate_coop_rank_for_score(coop_score)
        else:
            coop_score = 0
            coop_rank = None

        logger.info("creating game with id %s from server %s", data["tag"], server)
        try:
            with transaction.atomic():
                game = self.create(
                    server=server,
                    tag=data["tag"],
                    date_finished=date_finished,
                    gametype=gametype,
                    gametype_legacy=gametypes_reversed[data["gametype"]],
                    map=Map.objects.obtain_for(data["mapname"]),
                    mapname=mapnames_reversed.get(data["mapname"], -1),
                    outcome=data["outcome"],
                    outcome_legacy=outcome_reversed[data["outcome"]],
                    time=data["time"],
                    player_num=data["player_num"],
                    score_swat=data["score_swat"],
                    score_sus=data["score_sus"],
                    vict_swat=data["vict_swat"],
                    vict_sus=data["vict_sus"],
                    rd_bombs_defused=data["bombs_defused"],
                    rd_bombs_total=data["bombs_total"],
                    coop_score=coop_score,
                    coop_rank=coop_rank,
                )
        except IntegrityError as exc:
            logger.info("game with tag %s is already saved (%s)", data["tag"], exc)
            raise GameAlreadySavedError

        # now save rest of the data
        if coop_procedures:
            self._create_game_procedures(game, coop_procedures)
        if coop_objectives := data.get("coop_objectives"):
            self._create_game_objectives(game, coop_objectives)
        if players := data.get("players"):
            self._create_game_players(game, players)

        return game

    def _calculate_coop_score_for_procedures(self, procedures: list[dict[str, int]] | None) -> int:
        if procedures:
            return min(100, sum(proc["score"] for proc in procedures))
        return 0

    @classmethod
    def calculate_coop_rank_for_score(cls, score: int) -> CoopRank | None:
        for min_score, rank in cls.coop_min_score_for_rank:
            if score >= min_score:
                return rank
        return None

    def _create_game_procedures(self, game: "Game", procedures: list[dict[str, str]]) -> None:
        """Process COOP mission procedures"""
        from apps.tracker.models import Procedure

        Procedure.objects.bulk_create(
            [
                Procedure(
                    game=game,
                    name=procedure["name"],
                    name_legacy=procedures_reversed[procedure["name"]],
                    status=procedure["status"],
                    score=procedure["score"],
                )
                for procedure in procedures
            ]
        )

    def _create_game_objectives(self, game: "Game", objectives: list[dict[str, str]]) -> None:
        """Process COOP mission objectives"""
        from apps.tracker.models import Objective

        Objective.objects.bulk_create(
            [
                Objective(
                    game=game,
                    name=objective["name"],
                    name_legacy=objectives_reversed[objective["name"]],
                    status=objective["status"],
                    status_legacy=objective_status_reversed[objective["status"]],
                )
                for objective in objectives
            ]
        )

    def _create_game_players(self, game: "Game", players: list[dict[str, Any]]) -> None:
        """Process round players"""
        from apps.tracker.models import Alias, Loadout, Player, Weapon

        fields = [
            "team",
            "coop_status",
            "vip",
            "admin",
            "dropped",
            "score",
            "time",
            "kills",
            "teamkills",
            "deaths",
            "suicides",
            "arrests",
            "arrested",
            "kill_streak",
            "arrest_streak",
            "death_streak",
            "vip_captures",
            "vip_rescues",
            "vip_escapes",
            "vip_kills_valid",
            "vip_kills_invalid",
            "rd_bombs_defused",
            "sg_escapes",
            "sg_kills",
            "coop_hostage_arrests",
            "coop_hostage_hits",
            "coop_hostage_incaps",
            "coop_hostage_kills",
            "coop_enemy_arrests",
            "coop_enemy_incaps",
            "coop_enemy_kills",
            "coop_enemy_incaps_invalid",
            "coop_enemy_kills_invalid",
            "coop_toc_reports",
        ]

        for player_item in players:
            # handle empty and coloured names
            alias_name = force_name(player_item["name"], player_item["ip"])
            alias, _ = Alias.objects.match_or_create(name=alias_name, ip_address=player_item["ip"])
            player_obj = Player(
                game=game,
                alias=alias,
                ip=player_item["ip"],
                loadout=Loadout.objects.obtain(**player_item.get("loadout") or {}),
            )
            # numeric and boolean stats
            for field in fields:
                if field in player_item:
                    setattr(player_obj, field, player_item[field])

            player_obj.team_legacy = (
                teams_reversed[player_item["team"]] if "team" in player_item else None
            )
            player_obj.coop_status_legacy = (
                coop_status_reversed[player_item["coop_status"]]
                if "coop_status" in player_item
                else 0
            )
            player_obj.save()

            # don't create weapons for coop games
            if not game.is_coop_game and player_item.get("weapons"):
                Weapon.objects.bulk_create(
                    [
                        Weapon(
                            player=player_obj,
                            name=weapon["name"],
                            name_legacy=weapon_reversed[weapon["name"]],
                            time=weapon["time"],
                            shots=weapon["shots"],
                            hits=weapon["hits"],
                            teamhits=weapon["teamhits"],
                            kills=weapon["kills"],
                            teamkills=weapon["teamkills"],
                            # convert cm to meters
                            distance=weapon["distance"] / 100,
                        )
                        for weapon in player_item["weapons"]
                        if weapon["name"] != -1
                    ]
                )

    @classmethod
    def get_player_with_max_points(cls, game: "Game", field: str) -> GameTopFieldPlayer | None:
        """
        Return the player with the highest value of given field
        """
        players_with_field = [
            (player, getattr(player, field) or 0) for player in game.player_set.all()
        ]

        if not players_with_field:
            return None

        top_player, top_points = max(players_with_field, key=lambda item: item[1])
        return GameTopFieldPlayer(player=top_player, field=field, points=top_points)

    @classmethod
    def get_highlights_for_game(cls, game: "Game") -> list[GamePlayerHighlight]:
        """
        Return a list of notable game achievements credited to specific players.
        """
        items = []

        for title, description, field, min_points in cls.highlights:
            if not (player_with_max_points := cls.get_player_with_max_points(game, field)):
                continue

            if player_with_max_points.points < min_points:
                continue

            items.append(
                GamePlayerHighlight(
                    player=player_with_max_points.player,
                    title=title,
                    description=description % {"points": player_with_max_points.points},
                )
            )

        return items + cls._get_player_weapon_highlights(game)

    @classmethod
    def _get_player_weapon_highlights(cls, game: "Game") -> list[GamePlayerHighlight]:
        all_player_weapons = {}
        for player in game.player_set.all():
            for wpn in player.gun_weapons:
                if (
                    wpn.kills < cls.highlights_weapon_min_kills
                    or wpn.accuracy < cls.highlights_weapon_min_accuracy
                ):
                    continue
                all_player_weapons.setdefault(wpn.name, []).append((player, wpn))

        highlights = []
        # obtain the highest accuracy among all weapon users
        for weapon_name, weapon_users in all_player_weapons.items():
            top_user, top_user_weapon = max(weapon_users, key=lambda item: item[1].accuracy)
            highlights.append(
                GamePlayerHighlight(
                    player=top_user,
                    title=_("%(name)s Expert") % {"name": _(weapon_name)},
                    description=_("%(kills)s kills with average accuracy of %(accuracy)s%%")
                    % {
                        "kills": top_user_weapon.kills,
                        "accuracy": top_user_weapon.accuracy,
                    },
                )
            )

        return highlights

    def get_neighbors_for_game(self, game: "Game") -> GameNeighbors:
        qs = self.get_queryset().select_related("map", "server").filter(server=game.server)
        return GameNeighbors(
            prev=qs.filter(pk__lt=game.pk).order_by("-pk").first(),
            next=qs.filter(pk__gt=game.pk).order_by("pk").first(),
        )
