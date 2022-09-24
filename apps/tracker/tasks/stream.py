import logging

from django.db import transaction

from swat4stats.celery import app
from apps.tracker.models import Server, Game, Profile
from apps.tracker.signals import game_data_saved


__all__ = [
    'process_game_data',
    'update_profile_games',
]

logger = logging.getLogger(__name__)


@app.task(bind=True, default_retry_delay=60, max_retries=5)
@transaction.atomic
def process_game_data(self, server_id, data, data_received_at):
    """
    Attempt to save a game with given server

    :param server_id: Server instance id
    :param data: Validated game data
    :param data_received_at: Time the data was received at
    """
    server = Server.objects.get(pk=server_id)

    try:
        game = Game.objects.create_game(server=server, data=data, date_finished=data_received_at)
    except Game.DataAlreadySaved:
        pass
    except Exception as exc:
        logger.error('failed to create game due to %s', exc,
                     exc_info=True,
                     extra={'data': {'data': data}})
        self.retry(exc=exc)
    else:
        game_data_saved.send_robust(sender=None, data=data, server=server, game=game)


@app.task
@transaction.atomic
def update_profile_games(game_id):
    game = Game.objects.get(pk=game_id)
    queryset = Profile.objects.filter(alias__player__game=game)

    # the very first game
    (queryset
        .filter(game_first__isnull=True)
        .update(game_first=game,
                first_seen_at=game.date_finished))
    # to the latest game
    queryset.update(game_last=game, last_seen_at=game.date_finished)
