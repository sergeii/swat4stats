from datetime import datetime

import pytest
from pytz import UTC

from tests.factories.loadout import RandomLoadoutFactory
from tests.factories.tracker import (
    GameFactory,
    MapFactory,
    PlayerFactory,
    ProfileFactory,
    ServerFactory,
)


@pytest.fixture
def server(db):
    return ServerFactory()


def test_game_unknown_game_400(db, api_client):
    resp = api_client.get("/api/games/100500/")
    assert resp.status_code == 404


def test_get_game_detail_versus(db, settings, django_assert_num_queries, api_client, server):
    a_bomb = MapFactory(name="A-Bomb Nightclub")

    game = GameFactory(
        gametype="VIP Escort",
        map=a_bomb,
        server=server,
        date_finished=datetime(2017, 1, 1, tzinfo=UTC),
    )
    PlayerFactory(
        dropped=False,
        game=game,
        team="suspects",
        vip=False,
        loadout=RandomLoadoutFactory(head="Gas Mask", body="Heavy Armor"),
        alias__profile=ProfileFactory(
            team="swat",
            country="US",
            loadout=RandomLoadoutFactory(head="Helmet", body="Heavy Armor"),
        ),
    )
    PlayerFactory(
        dropped=False,
        game=game,
        team="swat",
        vip=True,
        loadout=RandomLoadoutFactory(head="None", body="None"),
    )
    PlayerFactory.create_batch(9, dropped=False, game=game)

    with django_assert_num_queries(8):
        resp = api_client.get(f"/api/games/{game.pk}/")

    assert resp.status_code == 200
    assert resp.data["map"]["name"] == "A-Bomb Nightclub"
    assert resp.data["server"]["hostname"] == server.hostname
    assert len(resp.data["players"]) == 11
    assert resp.data["coop_rank"] is None
    assert resp.data["rules"].startswith(
        "One player on the SWAT team is randomly chosen to be the VIP."
    )
    assert resp.data["briefing"] is None

    player_obj = resp.data["players"][0]
    assert player_obj["team"] == "suspects"
    assert player_obj["vip"] is False
    assert (
        player_obj["portrait_picture"]
        == f"{settings.STATIC_URL}images/portraits/suspects-heavy-armor-gas-mask.jpg"
    )
    assert player_obj["profile"]["country"] == "US"
    assert player_obj["profile"]["country_human"] == "United States of America"
    assert (
        player_obj["profile"]["portrait_picture"]
        == f"{settings.STATIC_URL}images/portraits/swat-heavy-armor-helmet.jpg"
    )


def test_get_game_detail_coop(db, django_assert_num_queries, api_client, server):
    game_map = MapFactory(name="A-Bomb Nightclub")
    coop_game = GameFactory(
        gametype="CO-OP",
        map=game_map,
        server=server,
        date_finished=datetime(2017, 1, 1, tzinfo=UTC),
        coop_score=77,
    )
    PlayerFactory.create_batch(7, dropped=False, game=coop_game)

    with django_assert_num_queries(8):
        resp = api_client.get(f"/api/games/{coop_game.pk}/")

    assert resp.status_code == 200
    assert resp.data["map"]["name"] == "A-Bomb Nightclub"
    assert resp.data["server"]["hostname"] == server.hostname
    assert len(resp.data["players"]) == 7
    assert resp.data["coop_rank"] == "Patrol Officer"
    assert resp.data["rules"].startswith(
        "Play single player missions with a group of up to five officers."
    )
    assert resp.data["briefing"].startswith(
        "We're being called up for a rapid deployment at an ongoing shots"
    )


@pytest.mark.parametrize("team", ["swat", "suspects"])
@pytest.mark.parametrize(
    "loadout_factory, image",
    [
        (
            lambda: RandomLoadoutFactory(head="Helmet", body="Light Armor"),
            "{team}-light-armor-helmet.jpg",
        ),
        (
            lambda: RandomLoadoutFactory(head="Gas Mask", body="Heavy Armor"),
            "{team}-heavy-armor-gas-mask.jpg",
        ),
        (lambda: RandomLoadoutFactory(head="None", body="Light Armor"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="Helmet", body="None"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="None", body="None"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="Helmet", body="Helmet"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="None", body="Helmet"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="Light Armor", body="Helmet"), "{team}.jpg"),
        (lambda: RandomLoadoutFactory(head="Light Armor", body="None"), "{team}.jpg"),
    ],
)
def test_get_game_detail_player_portrait(db, api_client, settings, team, loadout_factory, image):
    game = GameFactory()
    PlayerFactory(dropped=False, team=team, game=game, loadout=loadout_factory())

    resp = api_client.get(f"/api/games/{game.pk}/")
    assert resp.status_code == 200
    player = resp.data["players"][0]

    filename = image.format(team=team)
    assert player["portrait_picture"] == f"{settings.STATIC_URL}images/portraits/{filename}"


@pytest.mark.parametrize("team", ["swat", "suspects"])
@pytest.mark.parametrize(
    "loadout_factory",
    [
        lambda: RandomLoadoutFactory(head="Helmet", body="Light Armor"),
        lambda: RandomLoadoutFactory(head="Gas Mask", body="Heavy Armor"),
        lambda: RandomLoadoutFactory(head="None", body="Light Armor"),
        lambda: RandomLoadoutFactory(head="Helmet", body="None"),
        lambda: RandomLoadoutFactory(head="None", body="None"),
    ],
)
def test_get_game_detail_player_vip_portrait(db, api_client, settings, team, loadout_factory):
    game = GameFactory()
    PlayerFactory(dropped=False, vip=True, team=team, game=game, loadout=loadout_factory())

    resp = api_client.get(f"/api/games/{game.pk}/")
    assert resp.status_code == 200
    player = resp.data["players"][0]

    assert player["portrait_picture"] == f"{settings.STATIC_URL}images/portraits/vip.jpg"


@pytest.mark.parametrize(
    "map_name, map_image_name",
    [
        ("A-Bomb Nightclub", "a-bomb-nightclub.jpg"),
        ("Brewer County Courthouse", "brewer-county-courthouse.jpg"),
        ("St. Michael's Medical Center", "st-michaels-medical-center.jpg"),
        ("-EXP- Department of Agriculture", "exp-department-of-agriculture.jpg"),
        ("-EXP- Fresnal St. Station", "exp-fresnal-st-station.jpg"),
        ("Some Unknown Map", "intro.jpg"),
    ],
)
def test_get_game_map_picture(db, api_client, settings, map_name, map_image_name):
    game = GameFactory(map__name=map_name)

    resp = api_client.get(f"/api/games/{game.pk}/")
    assert resp.status_code == 200
    assert (
        resp.data["map"]["preview_picture"]
        == f"{settings.STATIC_URL}images/maps/preview/{map_image_name}"
    )
    assert (
        resp.data["map"]["background_picture"]
        == f"{settings.STATIC_URL}images/maps/background/{map_image_name}"
    )


@pytest.mark.parametrize(
    "map_name, briefing_snippet",
    [
        ("A-Bomb Nightclub", "We're being called up for a rapid deployment"),
        ("St. Michael's Medical Center", "Alright, men, we have an international incident"),
        ("-EXP- Department of Agriculture", "Okay, quiet down and listen."),
        ("-EXP- Fresnal St. Station", "The shit has really hit the fan."),
        ("Some Unknown Map", None),
    ],
)
def test_get_coop_game_map_briefing(db, api_client, map_name, briefing_snippet):
    game_map = MapFactory(name=map_name)
    coop_game = GameFactory(gametype="CO-OP", map=game_map)

    resp = api_client.get(f"/api/games/{coop_game.pk}/")

    if briefing_snippet is None:
        assert resp.data["briefing"] is None
    else:
        assert resp.data["briefing"].startswith(briefing_snippet)


def test_get_game_detail_neighboring_games(db, django_assert_num_queries, api_client, server):
    brewer = MapFactory(name="Brewer County Courthouse")
    northside = MapFactory(name="Northside Vending")

    prev_game = GameFactory(gametype="VIP Escort", server=server, map=brewer, score_swat=99)
    GameFactory.create_batch(2)

    game = GameFactory(gametype="VIP Escort", server=server, map=brewer)
    PlayerFactory.create_batch(3, dropped=False, game=game)

    GameFactory()
    next_game = GameFactory(gametype="VIP Escort", server=server, map=northside, score_sus=50)

    with django_assert_num_queries(8):
        resp = api_client.get(f"/api/games/{game.pk}/")

    prev_obj = resp.data["neighbors"]["prev"]
    assert prev_obj["id"] == prev_game.pk
    assert prev_obj["gametype"] == "VIP Escort"
    assert prev_obj["map"]["name"] == "Brewer County Courthouse"
    assert prev_obj["server"]["id"] == server.pk
    assert prev_obj["server"]["address"] == server.address
    assert prev_obj["score_swat"] == 99

    next_obj = resp.data["neighbors"]["next"]
    assert next_obj["id"] == next_game.pk
    assert next_obj["gametype"] == "VIP Escort"
    assert next_obj["map"]["name"] == "Northside Vending"
    assert next_obj["server"]["id"] == server.pk
    assert next_obj["server"]["address"] == server.address
    assert next_obj["score_sus"] == 50
