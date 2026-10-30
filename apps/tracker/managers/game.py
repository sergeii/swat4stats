import logging
import math
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import IntegrityError, models, transaction

from apps.tracker.entities import CoopRank, GameType
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
    from apps.tracker.models import Game, Server


logger = logging.getLogger(__name__)


class GameManager(models.Manager):
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
        server: Server,
        data: dict[str, Any],
        date_finished: datetime,
    ) -> Game:
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

    def _create_game_procedures(self, game: Game, procedures: list[dict[str, str]]) -> None:
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

    def _create_game_objectives(self, game: Game, objectives: list[dict[str, str]]) -> None:
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

    def _create_game_players(self, game: Game, players: list[dict[str, Any]]) -> None:
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
