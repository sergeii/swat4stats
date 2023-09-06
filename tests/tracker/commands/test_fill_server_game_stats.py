import pytest
from django.core.management import call_command

from apps.tracker.models import Server
from tests.factories.tracker import GameFactory, ServerFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_server_game_stats(django_assert_num_queries):
    server1, server2, server3, server4 = ServerFactory.create_batch(4)

    game1, game2, game3 = GameFactory.create_batch(3, server=server1)
    game4, game5 = GameFactory.create_batch(2, server=server2)
    game6 = GameFactory(server=server4)

    # server2 has some stats already
    Server.objects.filter(pk=server2.pk).update(
        game_count=1,
        first_game=game4,
        first_game_played_at=game4.date_finished,
        latest_game=game4,
        latest_game_played_at=game4.date_finished,
    )

    with django_assert_num_queries(7):
        call_command("fill_server_game_stats")

    server1.refresh_from_db()
    assert server1.game_count == 3
    assert server1.first_game.pk == game1.pk
    assert server1.first_game_played_at == game1.date_finished
    assert server1.latest_game.pk == game3.pk
    assert server1.latest_game_played_at == game3.date_finished

    # server2 didn't have its stats updated because it already had them
    server2.refresh_from_db()
    assert server2.game_count == 1
    assert server2.first_game.pk == game4.pk
    assert server2.first_game_played_at == game4.date_finished
    assert server2.latest_game.pk == game4.pk
    assert server2.latest_game_played_at == game4.date_finished

    # server3 has no games recorded
    server3.refresh_from_db()
    assert server3.game_count == 0
    assert server3.first_game is None
    assert server3.first_game_played_at is None
    assert server3.latest_game is None
    assert server3.latest_game_played_at is None

    # server4 has only one game
    server4.refresh_from_db()
    assert server4.game_count == 1
    assert server4.first_game.pk == game6.pk
    assert server4.first_game_played_at == game6.date_finished
    assert server4.latest_game.pk == game6.pk
    assert server4.latest_game_played_at == game6.date_finished
