from datetime import timedelta

from django.utils import timezone

from apps.tracker.models import Profile
from apps.tracker.signals import game_data_saved
from tests.factories.tracker import ServerFactory, GameFactory
from tests.factories.streaming import ServerGameDataFactory


def test_last_seen_is_updated_when_game_data_is_saved(db):
    then = timezone.now() - timedelta(days=1)
    game = GameFactory(date_finished=then, players=[{"alias__name": "Serge"}])

    game_data_saved.send(sender=None, data=ServerGameDataFactory(), server=game.server, game=game)

    profile = Profile.objects.get()

    assert game.date_finished
    assert profile.game_first.pk == game.pk
    assert profile.game_last.pk == game.pk
    assert profile.last_seen_at == then
    assert profile.first_seen_at == then


def test_server_is_relisted_when_data_is_saved(db):
    server = ServerFactory(listed=False, failures=4)
    game = GameFactory(
        server=server,
        gametype="VIP Escort",
        mapname=0,
        player_num=16,
        time=651,
        outcome="sus_vip_good_kill",
    )
    game_data_saved.send(
        sender=None,
        data=ServerGameDataFactory(),
        server=server,
        game=game,
    )
    server.refresh_from_db()
    assert server.listed
    assert server.failures == 0
