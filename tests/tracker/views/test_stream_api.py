from datetime import datetime, timedelta

from django.test import Client
from django.utils.timezone import now
from pytz import UTC
import pytest

from apps.geoip.factories import ISPFactory
from apps.tracker.factories import (
    ServerFactory,
    GameFactory,
    ServerGameDataFactory,
    PlayerGameDataFactory,
    SimplePlayerGameDataFactory,
    AliasFactory,
    ProfileFactory,
    WeaponGameDataFactory,
    ProcedureGameDataFactory,
    ObjectiveGameDataFactory,
    PlayerFactory,
    LoadoutFactory,
)
from apps.tracker.models import Game, Profile, Player, Server
from apps.utils.test import freeze_timezone_now


@pytest.fixture
def test_server(db):
    return ServerFactory(ip="127.0.0.1", port=10480)


@pytest.fixture
def test_game_data(db):
    return ServerGameDataFactory(
        tag="foobar",
        port=10480,
        gametype="Barricaded Suspects",
        version="9.9.9",
        players=[PlayerGameDataFactory(name="Serge", loadout__primary=10)],
    )


@pytest.fixture
def post_game_data(client):
    default_client = client

    def poster(game_data, *, client=None, **headers):
        client = client or default_client
        return client.post(
            "/stream/", game_data.to_json(), content_type="application/json", **headers
        )

    return poster


def assert_success_code(response):
    assert response.content.decode()[0] == "0"


def assert_error_code(response):
    assert response.content.decode()[0] == "1"


def test_get_redirects_to_main(db, client):
    response = client.get("/stream/")
    assert response.status_code == 302
    assert response.url == "/"


def test_stream_endpoint_method_bypasses_csrf_check(db, test_game_data, post_game_data):
    client = Client(enforce_csrf_checks=True, HTTP_X_REAL_IP="127.0.0.1")
    response = post_game_data(test_game_data, client=client)
    assert response.status_code == 200


def test_post_game_data(db, post_game_data):
    game_data = ServerGameDataFactory(
        tag="foobar",
        hostname="VIP Server",
        port=10580,
        gametype="VIP Escort",
        mapname="Children of Taronne Tenement",
        outcome=6,
        time=500,
        time_absolute=1000,
        score_swat=50,
        score_sus=45,
        vict_swat=1,
        vict_sus=0,
        player_num=2,
        version="1.1",
        players=[
            PlayerGameDataFactory(
                name="Serge",
                ip="127.0.0.23",
                dropped=True,
                admin=False,
                score=10,
                kills=7,
                kill_streak=10,
                death_streak=1,
                teamkills=1,
                suicides=1,
                deaths=1,
                team=0,
                time=100,
                arrested=2,
                loadout__primary=10,
                weapons=[
                    WeaponGameDataFactory(name=10, kills=5, hits=19, distance=900, teamkills=1),
                    WeaponGameDataFactory(
                        name=-1,  # skipped
                        kills=1,
                        hits=10,
                        distance=900,
                    ),
                ],
            ),
            PlayerGameDataFactory(
                name="Serge",
                ip="127.0.0.24",
                dropped=False,
                admin=True,
                team=1,
                score=25,
                kills=15,
                arrests=2,
                time=300,
                vip_captures=1,
                vip_rescues=1,
                kill_streak=10,
                death_streak=1,
                arrest_streak=2,
                deaths=1,
                loadout__primary=10,
                loadout__head=22,
                loadout__body=19,
                weapons=[
                    WeaponGameDataFactory(
                        name=10,
                        shots=200,
                        kills=10,
                        teamkills=0,
                        hits=20,
                        teamhits=1,
                        time=100,
                        distance=1000,
                    ),
                    WeaponGameDataFactory(name=25, kills=0, hits=10, teamhits=20),
                    WeaponGameDataFactory(name=11, kills=5, hits=20, teamhits=5, distance=1500),
                ],
            ),
            PlayerGameDataFactory(
                name="AnotherDude",
                ip="127.0.0.25",
                team=0,
                vip=1,
                score=15,
                kills=15,
                time=450,
                vip_escapes=1,
                loadout__primary=17,
                weapons=[WeaponGameDataFactory()],
            ),
        ],
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    # server is created
    server = Server.objects.get(ip="127.0.0.1", port=10580)
    assert server.enabled
    assert server.listed
    assert server.version == "1.1"
    assert server.hostname == "VIP Server"

    game = Game.objects.get()
    assert game.tag == "foobar"
    assert game.server == server
    assert game.gametype == "VIP Escort"
    assert game.map.name == "Children of Taronne Tenement"
    assert game.mapname == 2
    assert game.outcome == "swat_vip_escape"
    assert game.time == 500
    assert game.player_num == 2
    assert game.score_swat == 50
    assert game.score_sus == 45
    assert game.rd_bombs_defused == 0
    assert game.rd_bombs_total == 0

    profile1 = Profile.objects.get(alias__name="Serge")
    profile2 = Profile.objects.get(alias__name="AnotherDude")

    assert Profile.objects.count() == 2
    assert not profile1.team
    assert not profile1.loadout
    assert not profile1.country
    assert Player.objects.filter(alias__name="Serge").count() == 2

    assert not profile2.team
    assert not profile2.loadout
    assert not profile2.country
    assert Player.objects.filter(alias__name="AnotherDude").count() == 1

    player1 = Player.objects.get(ip="127.0.0.23", alias__profile=profile1)
    player2 = Player.objects.get(ip="127.0.0.24", alias__profile=profile1)
    player3 = Player.objects.get(ip="127.0.0.25", alias__profile=profile2)

    assert not player1.admin
    assert not player1.vip
    assert player1.dropped
    assert player1.team == "swat"
    assert player1.team_legacy == 0
    assert player1.score == 10
    assert player1.kills == 7
    assert player1.deaths == 1
    assert player1.arrested == 2
    assert player1.death_streak == 1
    assert player1.kill_streak == 10
    assert player1.teamkills == 1
    assert player1.time == 100
    assert player1.loadout.primary == "9mm SMG"

    assert player1.weapons.count() == 1
    player1_weapon = player1.weapons.get()
    assert player1_weapon.name == "9mm SMG"
    assert player1_weapon.kills == 5
    assert player1_weapon.hits == 19
    assert player1_weapon.distance == 9
    assert player1_weapon.teamkills == 1

    assert not player2.dropped
    assert player2.admin
    assert player2.team == "suspects"
    assert player2.team_legacy == 1
    assert player2.score == 25
    assert player2.kills == 15
    assert player2.arrests == 2
    assert player2.time == 300
    assert player2.deaths == 1
    assert player2.vip_captures == 1
    assert player2.vip_rescues == 1
    assert player2.kill_streak == 10
    assert player2.arrest_streak == 2
    assert player2.death_streak == 1
    assert player2.loadout.primary == "9mm SMG"
    assert player2.loadout.head == "Helmet"
    assert player2.loadout.body == "Light Armor"
    assert player2.weapons.count() == 3
    assert set(player2.weapons.values_list("name", flat=True)) == {
        "9mm SMG",
        "Suppressed 9mm SMG",
        "Stinger",
    }

    player2_weapon = player2.weapons.order_by("id")[:1].get()
    assert player2_weapon.name == "9mm SMG"
    assert player2_weapon.shots == 200
    assert player2_weapon.kills == 10
    assert player2_weapon.teamkills == 0
    assert player2_weapon.hits == 20
    assert player2_weapon.teamhits == 1
    assert player2_weapon.time == 100
    assert player2_weapon.distance == 10

    assert player3.vip
    assert player3.score == 15
    assert player3.kills == 15
    assert player3.time == 450
    assert player3.vip_escapes == 1
    assert player3.loadout.primary == "VIP Colt M1911 Handgun"
    assert player3.weapons.count() == 1


def test_post_game_data_with_players(db, whois_mock, post_game_data):
    whois_mock.side_effect = [
        {"nets": [{"description": "MekISP", "country": "nl", "cidr": "12.12.0.0/16"}]},
        {"nets": [{"cidr": "256.0.0.0/64"}]},
        {"nets": [{"description": "ScoISP", "cidr": "15.15.0.0/16"}]},
        {
            "nets": [
                {"description": "Another Norwegian ISP", "country": "no", "cidr": "16.16.0.0/16"}
            ]
        },
        {"nets": [{"description": "Finnish ISP", "country": "fi", "cidr": "17.17.0.0/16"}]},
        {"nets": [{"description": "Russian ISP", "country": "ru", "cidr": "18.18.0.0/16"}]},
    ]

    ISPFactory(ip="1.1.0.0/16", name="Local ISP", country="lo")
    ISPFactory(ip="9.9.0.0/16", name="Greek ISP", country="gr")
    ISPFactory(ip="10.10.0.0/16", name="Dutch ISP", country="nl")
    ISPFactory(ip="11.11.0.0/16", name="LOL ISP", country="kk")
    ISPFactory(ip="13.13.0.0/16", name="GG ISP", country="gg")

    empty_loadout = LoadoutFactory()
    semi_empty_loadout = LoadoutFactory(
        primary="M4 Super90",
        secondary="Taser Stun Gun",
        equip_one="Optiwand",
        equip_two="Flashbang",
    )
    full_loadout = LoadoutFactory(
        primary="M4 Super90",
        secondary="Taser Stun Gun",
        equip_one="Optiwand",
        equip_two="Flashbang",
        equip_three="Stinger",
        equip_four="Pepper Spray",
        equip_five="Pepper Spray",
        breacher="Shotgun",
        head="Helmet",
        body="Light Armor",
    )

    empty_isp_alias = AliasFactory(name="Bagwell", isp=None)
    nonempty_isp_alias = AliasFactory(name="Bagwell", isp=ISPFactory())  # noqa

    sco_isp_alias = AliasFactory(name="Scofield", isp__name="ScoISP", isp__ip="100.100.100.0/24")
    sco_another_alias = AliasFactory(  # noqa: F841
        name="Scofield", isp__name="AnoterScoISP", isp__ip="101.101.101.0/24"
    )
    burrows_country_alias = AliasFactory(
        name="Burrows",
        isp__ip="200.200.200.0/24",
        isp__name="Some Norwegian ISP",
        isp__country="no",
    )
    PlayerFactory(alias=burrows_country_alias, ip="200.200.200.188")

    heebo_player = PlayerFactory(
        ip="17.17.17.17",
        alias__name="Greebo",
        alias__isp=None,
        game__date_finished=now() - timedelta(days=20),
    )

    prophet_player = PlayerFactory(
        ip="18.18.18.18",
        alias__name="Coagulant",
        alias__isp=None,
        game__date_finished=now() - timedelta(days=365),
    )

    player_isp_alias = AliasFactory(
        name="Player", isp__name="PlayerISP", isp__country="gb", isp__ip="19.19.0.0/16"
    )

    game_data = ServerGameDataFactory(
        gametype="VIP Escort",
        player_num=16,
        players=[
            # dropped player
            PlayerGameDataFactory(name="Cris", ip="9.9.9.9", dropped=True),
            PlayerGameDataFactory(name="Cris", ip="9.9.9.9", dropped=False),
            # 2 players with same ip
            PlayerGameDataFactory(name="Sinaas", ip="10.10.12.12"),
            PlayerGameDataFactory(name="Stewie", ip="10.10.12.12"),
            # empty name
            PlayerGameDataFactory(name=r"[b][\b]", ip="11.11.11.11"),
            # new isp
            PlayerGameDataFactory(name="Mek", ip="12.12.12.12"),  # MOCK
            # existing isp
            PlayerGameDataFactory(name="Konten", ip="13.13.13.13"),
            # null isp
            PlayerGameDataFactory(name="Bagwell", ip="14.14.14.14"),  # MOCK
            # null loadout
            PlayerGameDataFactory(name="LoadoutPlayer", ip="1.1.12.124", loadout={}),
            # missing loadout
            SimplePlayerGameDataFactory(name="NoLoadoutPlayer", ip="1.1.18.12"),
            # semi null loadout
            PlayerGameDataFactory(
                name="SemiLoadoutPlayer", ip="1.1.18.19", loadout={0: 1, 2: 16, 4: 27, 5: 23}
            ),
            # full loadout
            PlayerGameDataFactory(
                name="FullLoadoutPlayer",
                ip="1.1.189.1",
                loadout={0: 1, 2: 16, 4: 27, 5: 23, 6: 25, 7: 26, 8: 26, 9: 3, 10: 19, 11: 22},
            ),
            # matched by name+isp
            PlayerGameDataFactory(name="scofield", ip="15.15.15.15"),  # MOCK
            # matched by name+country
            PlayerGameDataFactory(name="Burrows", ip="16.16.16.16"),  # MOCK
            # matched by ip
            PlayerGameDataFactory(name="Heebo", ip="17.17.17.17"),  # MOCK
            # not matched by old ip
            PlayerGameDataFactory(name="Prophet", ip="18.18.18.18"),  # MOCK
            # not matched by name+isp because name is popular
            PlayerGameDataFactory(name="player", ip="19.19.19.19"),  # MOCK
        ],
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get(tag=game_data["tag"])
    players = game.player_set.select_related("alias", "alias__isp", "alias__profile").order_by("id")
    (
        cris,
        cris2,
        sinaas,
        stewie,
        empty,
        mek,
        kont,
        bag,
        loadout_player,
        no_loadout_player,
        semi_loadout_player,
        full_loadout_player,
        sco,
        burrows,
        heebo,
        prophet,
        player,
    ) = players

    assert cris.dropped
    assert not cris2.dropped
    assert cris.alias == cris2.alias
    assert cris.alias.isp.name == "Greek ISP"
    assert cris.alias.isp.country == "gr"

    assert sinaas.alias.name == "Sinaas"
    assert sinaas.alias.isp.name == "Dutch ISP"
    assert stewie.alias.name == "Stewie"
    assert stewie.alias.isp.name == "Dutch ISP"
    assert sinaas.alias.profile == stewie.alias.profile
    assert sinaas.alias.profile.name == "Sinaas"

    assert empty.alias.name == "_438929d9"
    assert empty.alias.isp.country == "kk"

    assert mek.alias.isp.name == "MekISP"
    assert mek.alias.profile.name == "Mek"
    assert mek.alias.isp.country == "nl"

    assert kont.alias.isp.name == "GG ISP"

    assert bag.alias.isp is None
    assert bag.alias == empty_isp_alias

    assert loadout_player.loadout == empty_loadout

    for slot in [
        "primary",
        "primary_ammo",
        "secondary",
        "secondary_ammo",
        "equip_one",
        "equip_two",
        "equip_three",
        "equip_four",
        "equip_five",
        "breacher",
        "head",
        "body",
    ]:
        assert getattr(no_loadout_player.loadout, slot) == "None"
    assert semi_loadout_player.loadout == semi_empty_loadout
    assert full_loadout_player.loadout == full_loadout

    assert sco.alias != sco_isp_alias
    assert sco.alias.profile == sco_isp_alias.profile
    assert sco.alias.isp == sco_isp_alias.isp

    assert burrows.alias != burrows_country_alias
    assert burrows.alias.name == "Burrows"
    assert burrows.alias.isp.name == "Another Norwegian ISP"
    assert burrows.alias.profile == burrows_country_alias.profile

    assert heebo.alias != heebo_player.alias
    assert heebo.alias.name == "Heebo"
    assert heebo_player.alias.name == "Greebo"
    assert heebo_player.alias.profile == heebo.alias.profile

    assert prophet.alias.name == "Prophet"
    assert prophet.alias.profile != prophet_player.alias.profile
    assert prophet.alias.profile.name == "Prophet"

    assert player.alias != player_isp_alias
    assert player.alias.profile != player_isp_alias.profile
    assert player.alias.isp == player_isp_alias.isp


def test_post_data_to_enabled_server(db, post_game_data):
    server = ServerFactory(ip="127.0.0.1", port=11111, enabled=True)
    response = post_game_data(ServerGameDataFactory(tag="foobar", port=11111))
    assert_success_code(response)
    game = Game.objects.get()
    assert game.server == server
    assert game.tag == "foobar"


def test_post_data_to_disabled_server_error(db, post_game_data):
    ServerFactory(enabled=False, ip="127.0.0.1", port=11111)
    response = post_game_data(ServerGameDataFactory(port=11111))
    assert_error_code(response)
    assert Game.objects.count() == 0


def test_posting_data_makes_unlisted_server_relisted(db, test_game_data, post_game_data):
    server = ServerFactory(ip="127.0.0.1", port=10480, enabled=True, listed=False)
    post_game_data(test_game_data)
    server.refresh_from_db()
    assert server.listed
    assert server.version == "9.9.9"


def test_posting_duplicate_game_is_accepted(db, post_game_data):
    game_123 = GameFactory(tag="123")
    game_data = ServerGameDataFactory(tag="123", with_players_count=3)
    response = post_game_data(game_data)
    assert_success_code(response)

    assert Game.objects.get(tag="123").pk == game_123.pk
    assert game_123.player_set.count() == 0

    proper_game_data = ServerGameDataFactory(tag="456", with_players_count=3)
    response = post_game_data(proper_game_data)
    assert_success_code(response)
    game = Game.objects.get(tag="456")
    assert Game.objects.get(tag="123")
    assert game.pk != game_123.pk
    assert game.player_set.count() == 3


@pytest.mark.parametrize(
    "mapname, legacy_name, expected_name",
    [
        (1, 1, "Brewer County Courthouse"),
        ("-1", -1, "Unknown Map"),
        ("Unknown Map v2", -1, "Unknown Map v2"),
        (1000, -1, "1000"),
    ],
)
def test_schema_supports_map_numbers_and_names(
    db, post_game_data, mapname, legacy_name, expected_name
):
    game_data = ServerGameDataFactory(mapname=mapname)
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get(tag=game_data["tag"])
    assert game.map.name == expected_name
    assert game.mapname == legacy_name


@pytest.mark.parametrize(
    "gametype, legacy_name, expected_name",
    [
        (1, 1, "VIP Escort"),
        ("4", 4, "Smash And Grab"),
        ("CO-OP", 3, "CO-OP"),
    ],
)
def test_schema_supports_gametype_numbers_and_names(
    db, post_game_data, gametype, legacy_name, expected_name
):
    game_data = ServerGameDataFactory(gametype=gametype)
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get(tag=game_data["tag"])
    assert game.gametype == expected_name
    assert game.gametype_legacy == legacy_name


def test_schema_validates_unknown_gametype(db, post_game_data):
    game_data = ServerGameDataFactory(gametype="Unknown Gametype")
    response = post_game_data(game_data)
    assert_error_code(response)
    assert Game.objects.filter(tag=game_data["tag"]).count() == 0


@pytest.mark.parametrize("gamename", [0, 1, "SWAT 4", "SWAT 4X"])
def test_schema_supports_gamename_numbers_and_names(db, post_game_data, gamename):
    game_data = ServerGameDataFactory(gamename=gamename)
    response = post_game_data(game_data)
    assert_success_code(response)
    assert Game.objects.get(tag=game_data["tag"])


@pytest.mark.parametrize("gamename", [-1, 2, "SWAT", "SWAT X"])
def test_schema_validates_unknown_gamename(db, post_game_data, gamename):
    game_data = ServerGameDataFactory(gamename=gamename)
    response = post_game_data(game_data)
    assert_error_code(response)
    assert Game.objects.filter(tag=game_data["tag"]).count() == 0


def test_stream_endpoint_supports_both_encoded_and_literal_values(db, post_game_data):
    for mapname, expected_id, expected_name in [
        (1, 1, "Brewer County Courthouse"),
        ("-1", -1, "Unknown Map"),
        ("Unknown Map v2", -1, "Unknown Map v2"),
        (1000, -1, "1000"),
    ]:
        game_data = ServerGameDataFactory(mapname=mapname)
        post_game_data(game_data)
        assert Game.objects.get(tag=game_data["tag"]).map.name == expected_name
        assert Game.objects.get(tag=game_data["tag"]).mapname == expected_id

    for gametype, expected_name in [
        (1, "VIP Escort"),
        ("4", "Smash And Grab"),
        ("CO-OP", "CO-OP"),
    ]:
        game_data = ServerGameDataFactory(gametype=gametype)
        post_game_data(game_data)
        assert Game.objects.get(tag=game_data["tag"]).gametype == expected_name

    game_data = ServerGameDataFactory(gametype="Unknown Gametype")
    post_game_data(game_data)
    assert Game.objects.filter(tag=game_data["tag"]).count() == 0

    for gamename in [0, 1, "SWAT 4", "SWAT 4X"]:
        game_data = ServerGameDataFactory(gamename=gamename)
        response = post_game_data(game_data)
        assert_success_code(response)
        assert Game.objects.get(tag=game_data["tag"])

    for gamename in [-1, 2, "SWAT", "SWAT X"]:
        game_data = ServerGameDataFactory(gamename=gamename)
        response = post_game_data(game_data)
        assert_error_code(response)
        assert Game.objects.filter(tag=game_data["tag"]).count() == 0


def test_post_game_data_updates_player_profiles(db, post_game_data):
    game3 = GameFactory()
    game4 = GameFactory()
    profile1 = AliasFactory(name="Hodor", isp=ISPFactory(ip="1.1.1.0/24")).profile
    profile2 = ProfileFactory()
    profile3 = AliasFactory(
        name="Brandon",
        isp=ISPFactory(ip="5.5.5.0/24"),
        profile=ProfileFactory(
            game_first=game3,
            game_last=game3,
            first_seen_at=game3.date_finished,
            last_seen_at=game3.date_finished,
        ),
    ).profile
    profile4 = AliasFactory(
        name="Meera",
        isp=ISPFactory(ip="10.10.10.0/24"),
        profile=ProfileFactory(game_first=game4, first_seen_at=game4.date_finished, game_last=None),
    ).profile

    assert profile1.game_last is None
    assert profile1.game_first is None
    assert profile1.first_seen_at is None
    assert profile1.last_seen_at is None

    assert profile3.game_last is not None
    assert profile3.game_first is not None
    assert profile3.first_seen_at is not None
    assert profile3.last_seen_at is not None

    game_data = ServerGameDataFactory(
        players=[
            PlayerGameDataFactory(name="Hodor", ip="1.1.1.23"),
            PlayerGameDataFactory(name="Brandon", ip="5.5.5.109"),
            PlayerGameDataFactory(name="Meera", ip="10.10.10.223"),
        ]
    )

    game_time = datetime(2016, 3, 14, 12, 45, 12, tzinfo=UTC)
    with freeze_timezone_now(game_time):
        post_game_data(game_data)
    new_game = Game.objects.get(tag=game_data["tag"])
    assert new_game.date_finished == game_time
    assert new_game.player_set.count() == 3

    profile1.refresh_from_db()
    assert profile1.game_first == profile1.game_last == new_game
    assert profile1.first_seen_at == profile1.last_seen_at == game_time

    profile2.refresh_from_db()
    assert profile2.game_last is None
    assert profile2.game_first is None
    assert profile2.first_seen_at is None
    assert profile2.last_seen_at is None

    profile3.refresh_from_db()
    assert profile3.game_first == game3
    assert profile3.first_seen_at == game3.date_finished
    assert profile3.game_last == new_game
    assert profile3.last_seen_at == game_time

    profile4.refresh_from_db()
    assert profile4.game_first == game4
    assert profile4.first_seen_at == game4.date_finished
    assert profile4.game_last == new_game
    assert profile4.last_seen_at == game_time


def test_post_barricaded_suspects_game(db, post_game_data, test_server):
    game_data = ServerGameDataFactory(
        port=10480,
        gametype="Barricaded Suspects",
        mapname="-EXP- Drug Lab",
        outcome=1,
        player_num=3,
        players=PlayerGameDataFactory.create_batch(3),
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get()
    assert game.server == test_server
    assert game.map.name == "-EXP- Drug Lab"
    assert game.mapname == 18
    assert game.gametype == "Barricaded Suspects"
    assert game.gametype_legacy == 0
    assert game.outcome == "swat_bs"
    assert game.outcome_legacy == 1
    assert game.player_set.count() == 3


def test_post_rapid_deployment_game(db, post_game_data, test_server):
    game_data = ServerGameDataFactory(
        port=10480,
        gametype=2,
        outcome=4,
        player_num=8,
        bombs_defused=4,
        bombs_total=5,
        players=(
            PlayerGameDataFactory.create_batch(2, rd_bombs_defused=2, team=0)
            + PlayerGameDataFactory.create_batch(3, team=1, rd_crybaby=1)
        ),
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get()
    assert game.mapname == 4
    assert game.server == test_server
    assert game.gametype == "Rapid Deployment"
    assert game.gametype_legacy == 2
    assert game.outcome == "sus_rd"
    assert game.outcome_legacy == 4
    assert game.rd_bombs_defused == 4
    assert game.rd_bombs_total == 5
    assert game.player_set.count() == 5

    assert list(game.player_set.filter(team="swat").values("rd_bombs_defused")) == [
        {"rd_bombs_defused": 2},
        {"rd_bombs_defused": 2},
    ]
    assert game.player_set.filter(team="suspects").count() == 3


def test_post_vip_escort_game(db, post_game_data, test_server):
    game_data = ServerGameDataFactory(
        port=10480,
        gametype="VIP Escort",
        outcome=8,
        player_num=4,
        players=[
            PlayerGameDataFactory(name="Foo", vip_rescues=2, team=0),
            PlayerGameDataFactory(name="Bar", vip=1, team=0),
            PlayerGameDataFactory(name="Ham", vip_captures=3, team=1),
            PlayerGameDataFactory(name="Baz", vip_kills_invalid=1, team=1),
        ],
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get()
    assert game.server == test_server
    assert game.gametype == "VIP Escort"
    assert game.gametype_legacy == 1
    assert game.outcome == "swat_vip_bad_kill"
    assert game.outcome_legacy == 8
    assert game.player_set.count() == 4

    assert game.player_set.get(alias__name="Foo", team="swat", vip_rescues=2)
    assert game.player_set.get(alias__name="Bar", team="swat", vip=True)
    assert game.player_set.get(alias__name="Ham", team="suspects", vip_captures=3)
    assert game.player_set.get(alias__name="Baz", team="suspects", vip_kills_invalid=1)


def test_post_coop_game(db, post_game_data, test_server):
    game_data = ServerGameDataFactory(
        port=10480,
        gametype="CO-OP",
        mapname="Mt. Threshold Research Center",
        outcome=10,
        player_num=3,
        coop_procedures=[
            ProcedureGameDataFactory(name=1, status="10/10", score=-60),
            ProcedureGameDataFactory(name=3, status="4/10", score=18),
            ProcedureGameDataFactory(name=9, status="2/4", score=10),
            ProcedureGameDataFactory(name=11, status="1/5", score=-5),
            ProcedureGameDataFactory(name=14, status="1/1", score=-10),
        ],
        coop_objectives=[
            ObjectiveGameDataFactory(name=10, status=2),
            ObjectiveGameDataFactory(name=11, status=2),
            ObjectiveGameDataFactory(name=26, status=1),
        ],
        players=[
            PlayerGameDataFactory(
                name="Foo",
                team=0,
                coop_status=3,
                coop_hostage_arrests=12,
                coop_hostage_hits=2,
                coop_hostage_incaps=1,
                coop_enemy_arrests=12,
                coop_enemy_incaps=1,
                coop_toc_reports=12,
                weapons=[
                    WeaponGameDataFactory(
                        name=10,
                        kills=13,
                        hits=65,
                        distance=100,
                    ),
                ],
            ),
            PlayerGameDataFactory(
                name="Ham",
                team=0,
                coop_status=2,
                coop_hostage_arrests=12,
                coop_hostage_incaps=1,
                coop_enemy_arrests=12,
                coop_enemy_incaps=1,
                coop_enemy_kills=1,
                coop_enemy_incaps_invalid=1,
                coop_toc_reports=5,
            ),
            PlayerGameDataFactory(
                name="Baz",
                team=1,
                coop_status=1,
                coop_hostage_hits=1,
                coop_hostage_incaps=1,
                coop_hostage_kills=1,
                coop_enemy_incaps=1,
                coop_enemy_incaps_invalid=1,
                coop_enemy_kills=1,
                coop_enemy_kills_invalid=1,
                coop_toc_reports=1,
                weapons=[
                    WeaponGameDataFactory(
                        name=15,
                        kills=3,
                        hits=10,
                        distance=90,
                    )
                ],
            ),
        ],
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get()
    assert game.server == test_server
    assert game.gametype == "CO-OP"
    assert game.gametype_legacy == 3
    assert game.outcome == "coop_completed"
    assert game.outcome_legacy == 10
    assert game.is_coop_game
    assert game.coop_score == -47

    assert game.objective_set.count() == 3
    assert game.objective_set.get(name="Neutralize Alice Jenkins", status="Failed")
    assert game.objective_set.get(name="Bring order to chaos", status="Failed")
    assert game.objective_set.get(name="Rescue all of the civilians", status="Completed")

    assert game.procedure_set.count() == 5
    assert game.procedure_set.get(name="Suspects arrested", status="10/10", score=-60)
    assert game.procedure_set.get(name="Failed to report a downed officer", status="4/10", score=18)
    assert game.procedure_set.get(name="Injured a fellow officer", status="2/4", score=10)
    assert game.procedure_set.get(name="No suspects neutralized", status="1/5", score=-5)
    assert game.procedure_set.get(name="Player uninjured", status="1/1", score=-10)

    assert game.player_set.count() == 3
    player1 = game.player_set.get(alias__name="Foo", team="swat")
    assert player1.coop_status == "Injured"
    assert player1.coop_status_legacy == 3
    assert player1.coop_hostage_arrests == 12
    assert player1.coop_hostage_hits == 2
    assert player1.coop_hostage_incaps == 1
    assert player1.coop_enemy_arrests == 12
    assert player1.coop_enemy_incaps == 1
    assert player1.coop_toc_reports == 12

    player2 = game.player_set.get(alias__name="Ham", team="swat")
    assert player2.coop_status == "Healthy"
    assert player2.coop_status_legacy == 2
    assert player2.coop_hostage_arrests == 12
    assert player2.coop_hostage_incaps == 1
    assert player2.coop_enemy_arrests == 12
    assert player2.coop_enemy_incaps == 1
    assert player2.coop_enemy_kills == 1
    assert player2.coop_enemy_incaps_invalid == 1
    assert player2.coop_toc_reports == 5

    player3 = game.player_set.get(alias__name="Baz", team="suspects")
    assert player3.coop_status == "Ready"
    assert player3.coop_status_legacy == 1
    assert player3.coop_hostage_hits == 1
    assert player3.coop_hostage_incaps == 1
    assert player3.coop_hostage_kills == 1
    assert player3.coop_enemy_incaps == 1
    assert player3.coop_enemy_incaps_invalid == 1
    assert player3.coop_enemy_kills == 1
    assert player3.coop_enemy_kills_invalid == 1
    assert player3.coop_toc_reports == 1

    assert player1.weapons.count() == 0
    assert player2.weapons.count() == 0
    assert player3.weapons.count() == 0


def test_post_smash_and_grab_game(db, post_game_data, test_server):
    game_data = ServerGameDataFactory(
        port=10480,
        gametype="4",
        mapname="-EXP- Stetchkov Warehouse",
        outcome=13,
        player_num=3,
        players=[
            PlayerGameDataFactory(name="Foo", team=0),
            PlayerGameDataFactory(name="Ham", sg_kills=3, sg_crybaby=1, team=1),
            PlayerGameDataFactory(name="Baz", sg_kills=4, sg_crybaby=1, team=1),
        ],
    )
    response = post_game_data(game_data)
    assert_success_code(response)

    game = Game.objects.get()
    assert game.server == test_server
    assert game.gametype == "Smash And Grab"
    assert game.gametype_legacy == 4
    assert game.map.name == "-EXP- Stetchkov Warehouse"
    assert game.outcome == "sus_sg"
    assert game.outcome_legacy == 13
    assert game.player_set.count() == 3

    assert game.player_set.get(alias__name="Foo", team="swat")
    assert game.player_set.get(alias__name="Ham", team="suspects", sg_kills=3)
    assert game.player_set.get(alias__name="Baz", team="suspects", sg_kills=4)


@pytest.mark.parametrize(
    "game_data",
    [
        {"port": 1},
        {"port": 65535},
        {"gametype": "VIP Escort"},
        {"gametype": "CO-OP"},
        {"gametype": "CO-OP QMM"},
        {"gametype": 0},
        {"gametype": 5},
        {"gametype": 5},
        {"mapname": "-1"},
        {"mapname": 0},
        {"mapname": "Brewer County Courthouse"},
        {"gamename": 0},
        {"gamename": "SWAT 4X"},
        {"coop_procedures": [{"0": 0}]},
        {
            "coop_objectives": [
                {"0": 12},
                {"0": 1},
            ]
        },
        {"coop_procedures": [{"0": 0, "1": "1/1"}, {"0": 10, "1": "120/150"}]},
    ],
)
def test_post_good_stream_data(db, game_data, post_game_data):
    game_data = ServerGameDataFactory(**game_data)
    response = post_game_data(game_data)
    assert_success_code(response)
    assert Game.objects.get(tag=game_data["tag"])


@pytest.mark.parametrize(
    "game_data",
    [
        {"tag": None},
        {"port": -1},
        {"port": 70000},
        {"port": 0},
        {"timestamp": -100},
        {"extra_key": "value"},
        {"time": "string"},
        {"time": -1},
        {"vict_swat": -5},
        {"vict_sus": -1},
        {"gametype": "Unknown Gametype"},
        {"gametype": 6},
        {"coop_objectives": [{"0": "invalid"}]},
    ],
)
def test_malformed_stream_data(db, game_data, post_game_data):
    game_data = ServerGameDataFactory(**game_data)
    response = post_game_data(game_data)
    assert_error_code(response)
    assert Game.objects.count() == 0


@pytest.mark.parametrize(
    "data_encoder, content_type",
    [
        (lambda game: game.to_julia_v1(), "application/x-www-form-urlencoded"),
        (lambda game: game.to_julia_v2(), "application/x-www-form-urlencoded"),
        (lambda game: game.to_json(), "application/json"),
    ],
)
def test_various_data_forms_are_accepted(db, data_encoder, content_type, client):
    ISPFactory(country="un", ip="127.0.0.0/24")
    game_data = ServerGameDataFactory(
        tag="foobar",
        port=10480,
        gametype="VIP Escort",
        players=[PlayerGameDataFactory(name="Serge", loadout__primary=10, weapons__kills=9000)],
    )
    ServerFactory(ip="127.0.0.1", port=10480, enabled=True)

    data_encoded = data_encoder(game_data)
    response = client.post("/stream/", data_encoded, content_type=content_type)

    game = Game.objects.get()
    player = game.player_set.get()
    assert response.status_code == 200
    assert response.content.decode()[0] == "0"
    assert game.tag == "foobar"
    assert game.gametype == "VIP Escort"
    assert player.alias.name == "Serge"
    assert player.loadout.primary == "9mm SMG"
    assert player.weapons.count() > 0

    for weapon in player.weapons.all():
        assert weapon.kills == 9000


@pytest.mark.parametrize(
    "stream_ip, stream_port, server_id",
    [
        ("51.15.152.220", 11480, 3),
        ("51.15.152.220", 10480, 2),
        ("77.250.71.231", 10480, 5),
        ("116.203.36.143", 10580, 4),
        ("111.222.111.222", 10480, None),
    ],
)
def test_pick_correct_from_multiple_servers(db, post_game_data, stream_ip, stream_port, server_id):
    default_server_10480 = ServerFactory(ip="127.0.0.1", port=10480)
    server_10480 = ServerFactory(ip="51.15.152.220", port=10480)
    server_11480 = ServerFactory(ip="51.15.152.220", port=11480)
    server_10580 = ServerFactory(ip="116.203.36.143", port=10580)
    another_server_10480 = ServerFactory(ip="77.250.71.231", port=10480)

    servers = {
        1: default_server_10480,
        2: server_10480,
        3: server_11480,
        4: server_10580,
        5: another_server_10480,
    }

    game_data = ServerGameDataFactory(hostname="VIP Server", port=stream_port)
    response = post_game_data(game_data, HTTP_X_REAL_IP=stream_ip)
    assert_success_code(response)

    game = Game.objects.get()

    if server_id is None:
        new_server = Server.objects.get(ip=stream_ip, port=stream_port)
        assert game.server == new_server
        for test_server in servers.values():
            assert test_server.pk != new_server.pk
    else:
        assert game.server.pk == servers[server_id].pk
