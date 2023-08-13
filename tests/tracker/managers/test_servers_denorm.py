from datetime import datetime

import pytest
from pytz import UTC

from apps.tracker.models import Server
from apps.tracker.utils.misc import force_clean_name
from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import GameFactory, ServerFactory


def test_denorm_game_stats_for_servers(db):
    server1, server2, server3, server4, server5 = ServerFactory.create_batch(5)

    game1, game2, game3 = GameFactory.create_batch(3, server=server1)
    game4, game5 = GameFactory.create_batch(2, server=server2)
    game6 = GameFactory(server=server4)
    GameFactory.create_batch(2, server=server5)

    # server2 has some stats already
    Server.objects.filter(pk=server2.pk).update(
        game_count=1,
        first_game=game4,
        first_game_played_at=game4.date_finished,
        latest_game=game4,
        latest_game_played_at=game4.date_finished,
    )

    Server.objects.denorm_game_stats(server1, server2, server3, server4)

    server1.refresh_from_db()
    assert server1.game_count == 3
    assert server1.first_game.pk == game1.pk
    assert server1.first_game_played_at == game1.date_finished
    assert server1.latest_game.pk == game3.pk
    assert server1.latest_game_played_at == game3.date_finished

    # server2 got its stats recalculated
    server2.refresh_from_db()
    assert server2.game_count == 2
    assert server2.first_game.pk == game4.pk
    assert server2.first_game_played_at == game4.date_finished
    assert server2.latest_game.pk == game5.pk
    assert server2.latest_game_played_at == game5.date_finished

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

    # server5 was not updated
    server5.refresh_from_db()
    assert server5.game_count == 0
    assert server5.first_game is None
    assert server5.first_game_played_at is None
    assert server5.latest_game is None
    assert server5.latest_game_played_at is None


def test_update_existing_game_stats_for_server(db):
    server1, server2 = ServerFactory.create_batch(2)

    game1, game2, game3 = GameFactory.create_batch(3, server=server1)
    game4, game5 = GameFactory.create_batch(2, server=server2)

    Server.objects.filter(pk=server1.pk).update(
        game_count=1,
        first_game=game1,
        first_game_played_at=game1.date_finished,
        latest_game=game2,
        latest_game_played_at=game2.date_finished,
    )
    Server.objects.update_game_stats_with_game(game2)

    Server.objects.filter(pk=server2.pk).update(
        game_count=1,
        first_game=game3,
        first_game_played_at=game3.date_finished,
        latest_game=game4,
        latest_game_played_at=game4.date_finished,
    )
    Server.objects.update_game_stats_with_game(game5)

    server1.refresh_from_db()
    assert server1.game_count == 1
    assert server1.first_game == game1
    assert server1.first_game_played_at == game1.date_finished
    assert server1.latest_game == game2
    assert server1.latest_game_played_at == game2.date_finished

    server2.refresh_from_db()
    assert server2.game_count == 2
    assert server2.first_game == game3
    assert server2.first_game_played_at == game3.date_finished
    assert server2.latest_game == game5
    assert server2.latest_game_played_at == game5.date_finished


def test_update_game_stats_for_server_from_scratch(db):
    server = ServerFactory()
    game1, game2 = GameFactory.create_batch(2, server=server)

    Server.objects.update_game_stats_with_game(game1)
    server.refresh_from_db()
    assert server.game_count == 1
    assert server.first_game == game1
    assert server.first_game_played_at == game1.date_finished
    assert server.latest_game == game1
    assert server.latest_game_played_at == game1.date_finished

    Server.objects.update_game_stats_with_game(game2)
    server.refresh_from_db()
    assert server.game_count == 2
    assert server.first_game == game1
    assert server.first_game_played_at == game1.date_finished
    assert server.latest_game == game2
    assert server.latest_game_played_at == game2.date_finished

    # stats are not updated if the game is already saved as the latest
    Server.objects.update_game_stats_with_game(game2)
    server.refresh_from_db()
    assert server.game_count == 2
    assert server.first_game == game1
    assert server.first_game_played_at == game1.date_finished
    assert server.latest_game == game2
    assert server.latest_game_played_at == game2.date_finished


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC))
def test_update_search_vector_for_many_servers(now_mock, django_assert_num_queries):
    myt = ServerFactory(hostname_clean="-==MYT Team Svr==-")
    legends = ServerFactory(hostname_clean="Legends Never Die coooP =)")
    sog = ServerFactory(hostname_clean="Sog-team.co.uk Pro!")
    nrg = ServerFactory(hostname_clean="nRg Legacy| S&G")

    with django_assert_num_queries(4):
        Server.objects.update_search_vector(myt.pk, legends.pk, sog.pk, nrg.pk)

    for s in [myt, legends, sog, nrg]:
        s.refresh_from_db()
        assert s.search is not None
        assert s.search_updated_at == datetime(2023, 8, 8, 11, 22, 55, tzinfo=UTC)


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC))
@pytest.mark.parametrize(
    "hostname, tsv",
    [
        (
            "-==MYT Team Svr==-",
            "'myt':1A,4B,7B,10B,13B 'svr':3A,6B,9B,12B,15B 'team':2A,5B,8B,11B,14B",
        ),
        (
            "[c=4169e1]Sog-team.co.uk [c=00c500]P[c=00DB00]r[c=22FF22]o[C=6fff6f]!",
            "'co':9B,14B 'pro':2A,4B,6B,11B,16B 'sog':7B,12B 'sog-team.co.uk':1A,3B,5B 'team':8B,13B 'uk':10B,15B",  # noqa: E501
        ),
        (
            "[CN]SSF PVP Server",
            "'cn':1A,5B,9B,13B,17B 'pvp':3A,7B,11B,15B,19B 'server':4A,8B,12B,16B,20B 'ssf':2A,6B,10B,14B,18B",  # noqa: E501
        ),
        (
            "[c=ff0000]L[c=ffffff]egends [c=ff0000]N[c=ffffff]ever [c=ff0000]D[c=ffffff]ie [c=b000ff]c[c=a70bee]o[c=8a08c5]o[c=b83fee]o[c=be4af2]P [c=00ffff]=)",  # noqa: E501
            "'cooo':8B,21B 'cooop':4A,13B,17B 'die':3A,7B,12B,16B,20B 'legends':1A,5B,10B,14B,18B 'never':2A,6B,11B,15B,19B 'p':9B,22B",  # noqa: E501
        ),
        (
            "WWW.EPiCS.TOP",
            "'cs':10B 'cs.top':3B 'epi':9B 'epics':6B 'top':7B,11B 'www':5B,8B 'www.epi':2B 'www.epics.top':1A,4B",  # noqa: E501
        ),
        ("", ""),
        (None, ""),
    ],
)
def test_update_search_vector_for_one_server(now_mock, django_assert_num_queries, hostname, tsv):
    server = ServerFactory(
        hostname=hostname, hostname_clean=None if hostname is None else force_clean_name(hostname)
    )

    with django_assert_num_queries(4):
        Server.objects.update_search_vector(server.pk)

    server.refresh_from_db()
    assert server.search == tsv
    assert server.search_updated_at == datetime(2023, 8, 7, 11, 22, 55, tzinfo=UTC)
