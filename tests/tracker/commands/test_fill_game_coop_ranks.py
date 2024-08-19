import pytest
from django.core.management import call_command
from pytest_django import DjangoAssertNumQueries

from tests.factories.tracker import GameFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_game_coop_ranks(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    vip_game = GameFactory(gametype="VIP Escort", coop_score=0, coop_rank=None)
    bs_game = GameFactory(gametype="Barricaded Suspects", coop_score=0, coop_rank=None)
    coop_game_with_rank = GameFactory(gametype="CO-OP", coop_score=10, coop_rank="Recruit")
    coop_game1 = GameFactory(gametype="CO-OP", coop_score=-100, coop_rank=None)
    coop_game2 = GameFactory(gametype="CO-OP", coop_score=-1, coop_rank=None)
    coop_game3 = GameFactory(gametype="CO-OP", coop_score=0, coop_rank=None)
    coop_game4 = GameFactory(gametype="CO-OP", coop_score=51, coop_rank=None)
    coop_game5 = GameFactory(gametype="CO-OP", coop_score=100, coop_rank=None)
    coop_game6 = GameFactory(gametype="CO-OP", coop_score=101, coop_rank=None)

    with django_assert_num_queries(3):
        call_command("fill_game_coop_ranks", "--chunk-size", "100")

    for game in [
        vip_game,
        bs_game,
        coop_game_with_rank,
        coop_game1,
        coop_game2,
        coop_game3,
        coop_game4,
        coop_game5,
        coop_game6,
    ]:
        game.refresh_from_db()

    assert vip_game.coop_rank is None
    assert bs_game.coop_rank is None
    assert coop_game_with_rank.coop_rank == "Recruit"
    assert coop_game1.coop_rank == "Menace"
    assert coop_game2.coop_rank == "Menace"
    assert coop_game3.coop_rank == "Menace"
    assert coop_game4.coop_rank == "Recruit"
    assert coop_game5.coop_rank == "Chief Inspector"
    assert coop_game6.coop_rank == "Chief Inspector"
