import logging
from datetime import datetime
from typing import Any

import celery
from django.db import transaction

from apps.tracker.exceptions import GameDataAlreadySaved
from swat4stats.celery import app, Queue
from apps.tracker.models import Server, Game, Profile
from apps.tracker.signals import game_data_saved


__all__ = [
    'process_game_data',
    'update_profile_games',
]

logger = logging.getLogger(__name__)


@app.task(bind=True, default_retry_delay=60, max_retries=5, queue=Queue.default.value)
def process_game_data(
    self: celery.Task,
    server_id: int,
    data: dict[str, Any],
    data_received_at: datetime,
) -> None:
    """
    Attempt to save a game with given server

    :param server_id: Server instance id
    :param data: Validated game data
    :param data_received_at: Time the data was received at
    """
    server = Server.objects.get(pk=server_id)

    try:
        game = Game.objects.create_game(server=server, data=data, date_finished=data_received_at)
    except GameDataAlreadySaved:
        pass
    except Exception as exc:
        logger.error('failed to create game due to %s', exc,
                     exc_info=True,
                     extra={'data': {'data': data}})
        self.retry(exc=exc)
    else:
        game_data_saved.send_robust(sender=None, data=data, server=server, game=game)


@app.task(queue=Queue.default.value)
def update_profile_games(game_id: int) -> None:
    game = Game.objects.get(pk=game_id)
    queryset = Profile.objects.filter(alias__player__game=game)

    # the very first game
    with transaction.atomic(durable=True):
        (queryset
            .filter(game_first__isnull=True)
            .update(game_first=game,
                    first_seen_at=game.date_finished))
        # to the latest game
        queryset.update(game_last=game, last_seen_at=game.date_finished)
