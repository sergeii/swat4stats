import argparse
import logging
from typing import Any

from django.core.management.base import BaseCommand

from apps.tracker.entities import GameType
from apps.tracker.models import Game
from apps.utils.misc import iterate_queryset

logger = logging.getLogger(__name__)


def fill_coop_ranks(chunk_size: int) -> None:
    total = 0

    coop_game_ids = (
        Game.objects.using("replica")
        .filter(gametype=GameType.co_op, coop_rank__isnull=True)
        .only("pk")
    )

    for chunk in iterate_queryset(coop_game_ids, fields=["pk"], chunk_size=chunk_size):
        if not chunk:
            break

        game_ids = [game["pk"] for game in chunk]

        total += len(game_ids)
        logger.info(
            "updating coop ranks for %d games %s...%s (total %d)",
            len(game_ids),
            game_ids[0],
            game_ids[-1],
            total,
        )

        # fmt: off
        games_to_update = (
            Game.objects
            .filter(pk__in=game_ids, gametype=GameType.co_op, coop_rank__isnull=True)
            .only("coop_score")
        )
        # fmt: on
        for game_to_update in games_to_update:
            coop_rank = Game.objects.calculate_coop_rank_for_score(game_to_update.coop_score)
            game_to_update.coop_rank = coop_rank

        Game.objects.bulk_update(games_to_update, ["coop_rank"])


class Command(BaseCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-c", "--chunk-size", type=int, default=1000)

    def handle(self, *args: Any, **options: Any) -> None:
        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_coop_ranks(chunk_size=options["chunk_size"])
