from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tracker.models import Map
from tests.factories.tracker import GameFactory, MapFactory


@pytest.mark.django_db
def test_update_game_stats_for_map_for_existing() -> None:
    abomb = MapFactory(name="A-Bomb Nightclub")
    brewer = MapFactory(name="Brewer County Courthouse")

    game1, game2, game3 = GameFactory.create_batch(3, map=abomb)
    game4, game5 = GameFactory.create_batch(2, map=brewer)

    Map.objects.filter(pk=abomb.pk).update(
        game_count=1,
        first_game=game1,
        first_game_played_at=game1.date_finished,
        latest_game=game2,
        latest_game_played_at=game2.date_finished,
    )
    Map.objects.update_game_stats_with_game(game2)

    Map.objects.filter(pk=brewer.pk).update(
        game_count=1,
        first_game=game3,
        first_game_played_at=game3.date_finished,
        latest_game=game4,
        latest_game_played_at=game4.date_finished,
    )
    Map.objects.update_game_stats_with_game(game5)

    abomb.refresh_from_db()
    assert abomb.game_count == 1
    assert abomb.first_game == game1
    assert abomb.first_game_played_at == game1.date_finished
    assert abomb.latest_game == game2
    assert abomb.latest_game_played_at == game2.date_finished

    brewer.refresh_from_db()
    assert brewer.game_count == 2
    assert brewer.first_game == game3
    assert brewer.first_game_played_at == game3.date_finished
    assert brewer.latest_game == game5
    assert brewer.latest_game_played_at == game5.date_finished


@pytest.mark.django_db
def test_update_game_stats_for_map_from_scratch() -> None:
    abomb = MapFactory(name="A-Bomb Nightclub")
    brewer = MapFactory(name="Brewer County Courthouse")

    game1, game2 = GameFactory.create_batch(2, map=abomb)

    Map.objects.update_game_stats_with_game(game1)
    abomb.refresh_from_db()
    assert abomb.game_count == 1
    assert abomb.first_game == game1
    assert abomb.first_game_played_at == game1.date_finished
    assert abomb.latest_game == game1
    assert abomb.latest_game_played_at == game1.date_finished

    Map.objects.update_game_stats_with_game(game2)
    abomb.refresh_from_db()
    assert abomb.game_count == 2
    assert abomb.first_game == game1
    assert abomb.first_game_played_at == game1.date_finished
    assert abomb.latest_game == game2
    assert abomb.latest_game_played_at == game2.date_finished

    # check that the stats are not updated if the game is already the latest
    Map.objects.update_game_stats_with_game(game2)
    abomb.refresh_from_db()
    assert abomb.game_count == 2
    assert abomb.first_game == game1
    assert abomb.first_game_played_at == game1.date_finished
    assert abomb.latest_game == game2
    assert abomb.latest_game_played_at == game2.date_finished

    # check that game stats are not updated for other maps
    brewer.refresh_from_db()
    assert brewer.game_count == 0
    assert brewer.first_game is None
    assert brewer.first_game_played_at is None
    assert brewer.latest_game is None
    assert brewer.latest_game_played_at is None


@pytest.mark.django_db(databases=["default", "replica"])
@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (1000, 8),
        (4, 9),
        (2, 11),
    ],
)
def test_update_ratings_ok(
    django_assert_num_queries: Callable[[int], AbstractContextManager],
    chunk_size: int,
    expected_queries: int,
) -> None:
    now = timezone.now()

    abomb = MapFactory(name="A-Bomb Nightclub")
    brewer = MapFactory(name="Brewer County Courthouse")
    northside = MapFactory(name="Northside Vending", rating=2)
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse")
    new_library = MapFactory(name="New Library", rating=1)
    dead_end = MapFactory(name="DEAD_END")
    delta = MapFactory(name="DELTA CENTER")

    GameFactory.create_batch(3, map=dead_end, date_finished=now - timedelta(days=181))  # old games
    GameFactory.create_batch(4, map=delta)
    GameFactory.create_batch(3, map=new_library)
    GameFactory(map=abomb)
    GameFactory(map=warehouse)
    GameFactory.create_batch(2, map=brewer)

    with django_assert_num_queries(expected_queries):
        Map.objects.update_ratings(chunk_size=chunk_size)

    for obj in [abomb, brewer, northside, warehouse, new_library, dead_end, delta]:
        obj.refresh_from_db()

    assert abomb.rating == 1
    assert brewer.rating == 2
    assert warehouse.rating == 3
    assert delta.rating == 4
    assert new_library.rating == 5
    assert dead_end.rating is None
    assert northside.rating is None

    for obj in [abomb, brewer, warehouse, delta, new_library, dead_end, northside]:
        assert obj.rating_updated_at >= now

    GameFactory.create_batch(2, map=dead_end, date_finished=now - timedelta(days=1))
    GameFactory.create_batch(2, map=warehouse)

    then = timezone.now()
    Map.objects.update_ratings()

    for obj in [abomb, brewer, northside, warehouse, new_library, dead_end, delta]:
        obj.refresh_from_db()

    assert abomb.rating == 1
    assert brewer.rating == 2
    assert warehouse.rating == 3
    assert delta.rating == 4
    assert new_library.rating == 5
    assert dead_end.rating == 6
    assert northside.rating is None

    for obj in [abomb, brewer, warehouse, delta, new_library, dead_end, northside]:
        assert obj.rating_updated_at >= then


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_ratings_no_games(
    django_assert_num_queries: Callable[[int], AbstractContextManager],
) -> None:
    now = timezone.now()

    abomb = MapFactory(name="A-Bomb Nightclub", rating=1)
    northside = MapFactory(name="Northside Vending")
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse")
    delta = MapFactory(name="DELTA CENTER", rating=2)

    GameFactory(map=delta, date_finished=now - timedelta(days=181))

    # no games, no rating
    with django_assert_num_queries(7):
        Map.objects.update_ratings()

    for obj in [abomb, northside, warehouse, delta]:
        obj.refresh_from_db()
        assert obj.rating is None
        assert obj.rating_updated_at >= now
