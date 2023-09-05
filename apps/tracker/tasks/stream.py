import logging
from datetime import datetime
from typing import Any

import celery
from pytz import utc

from apps.tracker.exceptions import GameAlreadySavedError
from apps.tracker.models import Game, Map, Profile, Server
from apps.tracker.signals import game_data_saved
from swat4stats.celery import Queue, app

__all__ = [
    "process_game_data",
    "update_profile_games",
    "update_server_games",
    "update_map_games",
]

logger = logging.getLogger(__name__)


@app.task(bind=True, default_retry_delay=60, max_retries=5, queue=Queue.default.value)
def process_game_data(
    self: celery.Task,
    server_id: int,
    data: dict[str, Any],
    data_received_ts: float,
) -> None:
    """
    Attempt to save a game with given server

    :param server_id: Server instance id
    :param data: Validated game data
    :param data_received_at: Time the data was received at
    """
    data_received_at = datetime.fromtimestamp(data_received_ts, tz=utc)
    server = Server.objects.get(pk=server_id)

    try:
        game = Game.objects.create_game(server=server, data=data, date_finished=data_received_at)
    except GameAlreadySavedError:
        pass
    except Exception as exc:
        logger.exception("failed to create game due to %s", exc, extra={"data": {"data": data}})
        self.retry(exc=exc)
    else:
        game_data_saved.send_robust(sender=None, data=data, server=server, game=game)


@app.task(queue=Queue.default.value)
def update_profile_games(game_id: int) -> None:
    game = Game.objects.get(pk=game_id)
    Profile.objects.update_with_game(game)


@app.task(queue=Queue.default.value)
def update_server_games(game_id: int) -> None:
    game = Game.objects.get(pk=game_id)
    Server.objects.update_game_stats_with_game(game)


@app.task(queue=Queue.default.value)
def update_map_games(game_id: int) -> None:
    game = Game.objects.get(pk=game_id)
    Map.objects.update_game_stats_with_game(game)
