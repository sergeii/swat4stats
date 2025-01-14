from datetime import datetime
from unittest import mock
from urllib.parse import urlencode

import pytest
from pytz import UTC

from apps.tracker.utils.misc import force_clean_name
from apps.tracker.views import motd as motd_views
from apps.utils.test import freeze_timezone_now
from tests.factories.stats import GametypeStatsFactory, PlayerStatsFactory


def parse_content(content: bytes) -> list[str]:
    return [force_clean_name(line) for line in content.decode().split("\n")]


@pytest.fixture
def names():
    return [
        "Player",
        "Giocatore",
        "Jogador",
        "Spieler",
        "Gracz",
        "Killer",
        "David",
        "Pokemon",
        "Rambo",
        "Ghost",
        "Hitman",
        "Wolf",
        "Sniper",
    ]


@pytest.mark.parametrize("initial", [0, 60])
@pytest.mark.parametrize("limit", [1, 2, 10])
@pytest.mark.parametrize("repeat", [0, 100])
@pytest.mark.parametrize("delay", [True, False])
def test_motd_leaderboard(db, names, client, initial, limit, repeat, delay):
    for i, name in enumerate(names[:7]):
        PlayerStatsFactory(category="score", year=2021, position=i + 1, profile__name=name)

    qs = {"initial": initial, "limit": limit, "repeat": repeat}
    if delay:
        qs["delay"] = 1
    else:
        qs["nodelay"] = 1

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get(f"/api/motd/leaderboard/score/?{urlencode(qs)}")
        lines = parse_content(response.content)

        assert lines[0] == f"{initial}\t{repeat}"
        assert lines[1] == f"example.com - TOP {limit} by Score"

        num_players = min(limit, 7)
        offset = 0
        for i in range(num_players):
            offset += 3
            if delay:
                assert lines[offset] == f"{initial + i + 1}\t{repeat}"
            else:
                assert lines[offset] == f"{initial}\t{repeat}"
            assert lines[offset + 1] == f"#{i + 1} - {names[i]}"

        offset += 3
        if delay:
            assert lines[offset] == f"{initial + num_players + 1}\t{repeat}"
        else:
            assert lines[offset] == f"{initial}\t{repeat}"
        assert lines[offset + 1] == "Feel free to visit example.com to see more"


def test_motd_random_leaderboard(db, names, client):
    for i, name in enumerate(names[7:]):
        PlayerStatsFactory(category="arrests", year=2021, position=i + 1, profile__name=name)

    with (
        freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)),
        mock.patch.object(motd_views, "choice") as choice_mock,
    ):
        choice_mock.return_value = "arrests"
        response = client.get("/api/motd/leaderboard/")
        assert response.status_code == 200

        lines = parse_content(response.content)
        assert lines[0] == "60\t0"
        assert lines[1] == "example.com - TOP 5 by Arrests"
        assert lines[4] == "#1 - Pokemon"
        assert lines[7] == "#2 - Rambo"
        assert lines[18] == "66\t0"
        assert lines[19] == "Feel free to visit example.com to see more"

        choice_mock.assert_called_once_with(
            [
                "score",
                "top_score",
                "time",
                "wins",
                "kills",
                "arrests",
                "top_kill_streak",
                "top_arrest_streak",
                "spm_ratio",
                "spr_ratio",
                "kd_ratio",
                "weapon_hit_ratio",
            ]
        )


@pytest.mark.parametrize(
    "category, ok",
    [
        ("foo", False),
        ("score", True),
        ("kills", True),
        ("rd_bombs_defused", True),
        ("vip_captures", True),
        ("sg_escapes", True),
        ("coop_games", True),
        ("spm_ratio", True),
        ("teamkills", False),
    ],
)
def test_motd_leaderboard_validate_category(db, client, category, ok):
    response = client.get(f"/api/motd/leaderboard/{category}/")
    if ok:
        assert response.status_code == 200
    else:
        assert response.status_code == 400


@pytest.mark.parametrize(
    "params, ok",
    [
        ({}, True),
        ({"nodelay": 1}, True),
        ({"limit": -1}, False),
        ({"limit": 0}, False),
        ({"limit": 1}, True),
        ({"limit": 20}, True),
        ({"limit": 21}, False),
        ({"initial": 0}, True),
        ({"initial": -1}, False),
        ({"initial": 100}, True),
        ({"initial": 100, "repeat": -1}, False),
        ({"initial": 100, "repeat": 0}, True),
        ({"initial": 100, "repeat": 10}, True),
        ({"initial": 100, "repeat": 10, "limit": 0}, False),
        ({"initial": 100, "repeat": 10, "limit": 5}, True),
        ({"initial": 100, "repeat": 10, "limit": 5, "nodelay": 1}, True),
    ],
)
@pytest.mark.parametrize("with_players", [True, False])
def test_motd_leaderboard_validate_params(db, client, with_players, params, ok):
    if with_players:
        for i in range(5):
            PlayerStatsFactory(category="score", year=2021, position=i)

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get(f"/api/motd/leaderboard/score/?{urlencode(params)}")
        if ok:
            assert response.status_code == 200
            if not with_players:
                assert response.content == b"\n"
        else:
            assert response.status_code == 400
            assert response.content == b""


def test_motd_leaderboard_defaults(db, names, client):
    for i, name in enumerate(names):
        PlayerStatsFactory(category="score", year=2021, position=i + 1, profile__name=name)

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get("/api/motd/leaderboard/score/")
        lines = parse_content(response.content)
        assert lines[0] == "60\t0"
        assert lines[1] == "example.com - TOP 5 by Score"

        assert lines[3] == "61\t0"
        assert lines[4] == "#1 - Player"

        assert lines[6] == "62\t0"
        assert lines[7] == "#2 - Giocatore"

        assert lines[9] == "63\t0"
        assert lines[10] == "#3 - Jogador"

        assert lines[12] == "64\t0"
        assert lines[13] == "#4 - Spieler"

        assert lines[15] == "65\t0"
        assert lines[16] == "#5 - Gracz"

        assert lines[18] == "66\t0"
        assert lines[19] == "Feel free to visit example.com to see more"


@pytest.mark.parametrize(
    "day, month, year, effective",
    [
        (31, 12, 2020, 2020),
        (1, 1, 2021, 2020),
        (10, 1, 2021, 2020),
        (17, 1, 2021, 2021),
        (20, 6, 2021, 2021),
    ],
)
def test_motd_leaderboard_select_effective_year(db, names, client, day, month, year, effective):
    for i, name in enumerate(names[:7]):
        PlayerStatsFactory(category="score", year=2020, position=i + 1, profile__name=name)
    for i, name in enumerate(names[7:]):
        PlayerStatsFactory(category="score", year=2021, position=i + 1, profile__name=name)

    with freeze_timezone_now(datetime(year, month, day, 12, 17, 1, tzinfo=UTC)):
        response = client.get("/api/motd/leaderboard/score/")
        lines = parse_content(response.content)
        assert lines[0] == "60\t0"
        assert lines[1] == "example.com - TOP 5 by Score"

        if effective == 2020:
            assert lines[4] == "#1 - Player"
            assert lines[7] == "#2 - Giocatore"
        else:
            assert lines[4] == "#1 - Pokemon"
            assert lines[7] == "#2 - Rambo"


def test_motd_leaderboard_no_players_no_content(db, client):
    PlayerStatsFactory.create_batch(5, category="score", year=2021, position=None)
    for i in range(5):
        PlayerStatsFactory(category="kills", year=2021, position=i)
    for i in range(5):
        PlayerStatsFactory(category="score", year=2020, position=i)

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get("/api/motd/leaderboard/score/")
        assert response.status_code == 200
        assert response.content == b"\n"


@pytest.mark.parametrize(
    "alias, category, title",
    [
        ("score", "score", "Score"),
        ("time", "time", "Time Played"),
        ("wins", "wins", "Wins"),
        ("spm", "spm_ratio", "Score/Minute"),
        ("spm_ratio", "spm_ratio", "Score/Minute"),
        ("top_score", "top_score", "Best Score"),
        ("kills", "kills", "Kills"),
        ("arrests", "arrests", "Arrests"),
        ("kdr", "kd_ratio", "K/D Ratio"),
        ("kd_ratio", "kd_ratio", "K/D Ratio"),
        ("accuracy", "weapon_hit_ratio", "Accuracy"),
        ("ammo_accuracy", "weapon_hit_ratio", "Accuracy"),
        ("kill_streak", "top_kill_streak", "Best Kill Streak"),
        ("top_kill_streak", "top_kill_streak", "Best Kill Streak"),
        ("arrest_streak", "top_arrest_streak", "Best Arrest Streak"),
        ("top_arrest_streak", "top_arrest_streak", "Best Arrest Streak"),
    ],
)
def test_motd_leaderboard_categories_compat(db, client, names, alias, category, title):
    for i, name in enumerate(names[:7]):
        PlayerStatsFactory(category=category, year=2021, position=i + 1, profile__name=name)

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get(f"/api/motd/leaderboard/{alias}/")
        assert response.status_code == 200
        lines = parse_content(response.content)
        assert lines[0] == "60\t0"
        assert lines[1] == f"example.com - TOP 5 by {title}"
        assert lines[4] == "#1 - Player"
        assert lines[7] == "#2 - Giocatore"


@pytest.mark.parametrize(
    "category, gametype, title",
    [
        ("vip_escapes", "VIP Escort", "VIP Escapes"),
        ("vip_captures", "VIP Escort", "VIP Captures"),
        ("vip_rescues", "VIP Escort", "VIP Rescues"),
        ("vip_kills_valid", "VIP Escort", "VIP Kills"),
        ("rd_bombs_defused", "Rapid Deployment", "Bombs Disarmed"),
        ("sg_escapes", "Smash And Grab", "Case Escapes"),
        ("sg_kills", "Smash And Grab", "Case Carrier Kills"),
        ("coop_score", "CO-OP", "CO-OP Score"),
        ("coop_time", "CO-OP", "Time Played"),
        ("coop_games", "CO-OP", "Missions Played"),
        ("coop_wins", "CO-OP", "Missions Completed"),
        ("coop_enemy_arrests", "CO-OP", "Suspects Arrested"),
        ("coop_enemy_kills", "CO-OP", "Suspects Neutralized"),
        ("coop_toc_reports", "CO-OP", "TOC Reports"),
    ],
)
def test_motd_leaderboard_gametype_categories_compat(db, client, names, category, gametype, title):
    for i, name in enumerate(names[:7]):
        GametypeStatsFactory(
            category=category, year=2021, gametype=gametype, position=i + 1, profile__name=name
        )

    with freeze_timezone_now(datetime(2021, 5, 29, 12, 17, 1, tzinfo=UTC)):
        response = client.get(f"/api/motd/leaderboard/{category}/")
        assert response.status_code == 200
        lines = parse_content(response.content)
        assert lines[0] == "60\t0"
        assert lines[1] == f"example.com - TOP 5 by {title}"
        assert lines[4] == "#1 - Player"
        assert lines[7] == "#2 - Giocatore"
