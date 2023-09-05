import pytest
from django.core.management import call_command

from apps.tracker.models import Map
from tests.factories.tracker import GameFactory, MapFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_server_game_stats(django_assert_num_queries):
    map1, map2, map3, map4 = MapFactory.create_batch(4)

    game1, game2, game3 = GameFactory.create_batch(3, map=map1)
    game4, game5 = GameFactory.create_batch(2, map=map2)
    game6 = GameFactory(map=map4)

    # map2 has some stats already
    Map.objects.filter(pk=map2.pk).update(
        game_count=1,
        first_game=game4,
        first_game_played_at=game4.date_finished,
        latest_game=game4,
        latest_game_played_at=game4.date_finished,
    )

    with django_assert_num_queries(7):
        call_command("fill_map_game_stats")

    map1.refresh_from_db()
    assert map1.game_count == 3
    assert map1.first_game.pk == game1.pk
    assert map1.first_game_played_at == game1.date_finished
    assert map1.latest_game.pk == game3.pk
    assert map1.latest_game_played_at == game3.date_finished

    # map2 didn't have its stats updated because it already had them
    map2.refresh_from_db()
    assert map2.game_count == 1
    assert map2.first_game.pk == game4.pk
    assert map2.first_game_played_at == game4.date_finished
    assert map2.latest_game.pk == game4.pk
    assert map2.latest_game_played_at == game4.date_finished

    # map3 has no games recorded
    map3.refresh_from_db()
    assert map3.game_count == 0
    assert map3.first_game is None
    assert map3.first_game_played_at is None
    assert map3.latest_game is None
    assert map3.latest_game_played_at is None

    # map4 has only one game
    map4.refresh_from_db()
    assert map4.game_count == 1
    assert map4.first_game.pk == game6.pk
    assert map4.first_game_played_at == game6.date_finished
    assert map4.latest_game.pk == game6.pk
    assert map4.latest_game_played_at == game6.date_finished
