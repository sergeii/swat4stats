import urllib.parse

import pytest
from django.utils import timezone

from apps.tracker.models import Server
from tests.factories.tracker import ServerFactory


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def update_search_vector_for_servers():
    def updater():
        server_ids = Server.objects.values_list("pk", flat=True)
        Server.objects.update_search_vector(*server_ids)

    return updater


@pytest.fixture(autouse=True)
def _setup_servers(now, db, update_search_vector_for_servers):
    today = now
    yesterday = now - timezone.timedelta(days=1)
    two_days_ago = now - timezone.timedelta(days=2)
    three_days_ago = now - timezone.timedelta(days=3)
    four_days_ago = now - timezone.timedelta(days=4)

    ServerFactory(
        hostname_clean="-==MYT Team Svr==-",
        country="DE",
        game_count=1000,
        latest_game_played_at=today,
    )
    ServerFactory(
        hostname_clean="-==MYT World Svr==-",
        country="DE",
        game_count=250,
        latest_game_played_at=three_days_ago,
    )
    ServerFactory(
        hostname_clean="-==MYT Coop Svr==-",
        country="DE",
        game_count=500,
        latest_game_played_at=four_days_ago,
    )
    ServerFactory(
        hostname_clean="-==MYT Coop Pro Svr==-",
        country="DE",
        game_count=100,
        latest_game_played_at=three_days_ago,
    )

    ServerFactory(
        hostname_clean="Frosty's Playhouse TSS - VIP",
        game_count=100,
        country="US",
        latest_game_played_at=today,
    )
    ServerFactory(
        hostname_clean="Frosty's Playhouse TSS - BS",
        game_count=150,
        country="US",
        latest_game_played_at=two_days_ago,
    )

    ServerFactory(
        hostname_clean="nRg|discord.gg", country="RU", game_count=1000, latest_game_played_at=today
    )
    ServerFactory(
        hostname_clean="Sog-team.co.uk Pro!",
        country="GB",
        game_count=500,
        latest_game_played_at=yesterday,
    )
    ServerFactory(
        hostname_clean="WWW.EPiCS.TOP",
        country="DE",
        game_count=750,
        latest_game_played_at=four_days_ago,
    )
    ServerFactory(
        hostname_clean="[CN]SWAT4X COOP Server",
        country="DE",
        game_count=50,
        latest_game_played_at=two_days_ago,
    )

    # no game played yet, should not be present in the search results
    ServerFactory(hostname_clean="Swat4 Server", country="DE", latest_game_played_at=None)

    update_search_vector_for_servers()


@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_no_filters(api_client, django_assert_max_num_queries):
    with django_assert_max_num_queries(3):
        resp = api_client.get("/api/search/servers/")

    assert resp.status_code == 200

    assert resp.data["previous"] is None
    assert resp.data["next"] is None

    names = [obj["item"]["name_clean"] for obj in resp.data["results"]]
    assert names == [
        "-==MYT Team Svr==-",
        "Frosty's Playhouse TSS - VIP",
        "nRg|discord.gg",
        "Sog-team.co.uk Pro!",
        "Frosty's Playhouse TSS - BS",
        "[CN]SWAT4X COOP Server",
        "-==MYT World Svr==-",
        "-==MYT Coop Pro Svr==-",
        "-==MYT Coop Svr==-",
        "WWW.EPiCS.TOP",
    ]


@pytest.mark.parametrize(
    "query_params, expected_names",
    # fmt: off
    [
        # default ordering
        (
            {},
            [
                "-==MYT Team Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "nRg|discord.gg",
                "Sog-team.co.uk Pro!",
                "Frosty's Playhouse TSS - BS",
                "[CN]SWAT4X COOP Server",
                "-==MYT World Svr==-",
                "-==MYT Coop Pro Svr==-",
                "-==MYT Coop Svr==-",
                "WWW.EPiCS.TOP",
            ],
        ),
        # ordering by last played game desc, same as default
        (
            {"ordering": "-latest_game_played_at"},
            [
                "-==MYT Team Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "nRg|discord.gg",
                "Sog-team.co.uk Pro!",
                "Frosty's Playhouse TSS - BS",
                "[CN]SWAT4X COOP Server",
                "-==MYT World Svr==-",
                "-==MYT Coop Pro Svr==-",
                "-==MYT Coop Svr==-",
                "WWW.EPiCS.TOP",
            ],
        ),
        # ordering by last played game asc
        (
            {"ordering": "latest_game_played_at"},
            [
                "-==MYT Coop Svr==-",
                "WWW.EPiCS.TOP",
                "-==MYT World Svr==-",
                "-==MYT Coop Pro Svr==-",
                "Frosty's Playhouse TSS - BS",
                "[CN]SWAT4X COOP Server",
                "Sog-team.co.uk Pro!",
                "-==MYT Team Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "nRg|discord.gg",
            ],
        ),
        # ordering by game_count asc
        (
            {"ordering": "game_count"},
            [
                "[CN]SWAT4X COOP Server",
                "-==MYT Coop Pro Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "Frosty's Playhouse TSS - BS",
                "-==MYT World Svr==-",
                "-==MYT Coop Svr==-",
                "Sog-team.co.uk Pro!",
                "WWW.EPiCS.TOP",
                "-==MYT Team Svr==-",
                "nRg|discord.gg",
            ],
        ),
        # ordering by game_count desc
        (
            {"ordering": "-game_count"},
            [
                "-==MYT Team Svr==-",
                "nRg|discord.gg",
                "WWW.EPiCS.TOP",
                "-==MYT Coop Svr==-",
                "Sog-team.co.uk Pro!",
                "-==MYT World Svr==-",
                "Frosty's Playhouse TSS - BS",
                "-==MYT Coop Pro Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "[CN]SWAT4X COOP Server",
            ],
        ),
        # ordering by last played game asc, limit applied
        (
            {"ordering": "latest_game_played_at", "limit": 3},
            [
                "-==MYT Coop Svr==-",
                "WWW.EPiCS.TOP",
                "-==MYT World Svr==-",
            ],
        ),
        # ordering by last played game desc, limit applied
        (
            {"ordering": "-latest_game_played_at", "limit": 3},
            [
                "-==MYT Team Svr==-",
                "Frosty's Playhouse TSS - VIP",
                "nRg|discord.gg",
            ],
        ),
        # order by last played game, filter by country
        (
            {"ordering": "latest_game_played_at", "country": "DE"},
            [
                "-==MYT Coop Svr==-",
                "WWW.EPiCS.TOP",
                "-==MYT World Svr==-",
                "-==MYT Coop Pro Svr==-",
                "[CN]SWAT4X COOP Server",
                "-==MYT Team Svr==-",
            ],
        ),
        # search by hostname, order by last played game desc
        (
            {"ordering": "-latest_game_played_at", "q": "coop"},
            [
                "[CN]SWAT4X COOP Server",
                "-==MYT Coop Pro Svr==-",
                "-==MYT Coop Svr==-",
            ],
        ),
        # search by hostname, order by last played game asc
        (
            {"ordering": "latest_game_played_at", "q": "coop"},
            [
                "-==MYT Coop Svr==-",
                "-==MYT Coop Pro Svr==-",
                "[CN]SWAT4X COOP Server",
            ],
        ),
    ],
    # fmt: on
    ids=str,
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_ordering(api_client, query_params, expected_names):
    resp = api_client.get("/api/search/servers/", query_params)
    assert resp.status_code == 200
    names = [obj["item"]["name_clean"] for obj in resp.data["results"]]
    assert names == expected_names


@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_pagination_no_filters(api_client):
    resp = api_client.get("/api/search/servers/?limit=7")
    assert resp.status_code == 200

    assert resp.data["previous"] is None
    assert resp.data["count"] == 10

    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == [
        "-==MYT Team Svr==-",
        "Frosty's Playhouse TSS - VIP",
        "nRg|discord.gg",
        "Sog-team.co.uk Pro!",
        "Frosty's Playhouse TSS - BS",
        "[CN]SWAT4X COOP Server",
        "-==MYT World Svr==-",
    ]

    next_url = urllib.parse.urlparse(resp.data["next"])
    assert next_url.path == "/api/search/servers/"
    assert next_url.query == "limit=7&offset=7"

    resp = api_client.get(resp.data["next"])
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == [
        "-==MYT Coop Pro Svr==-",
        "-==MYT Coop Svr==-",
        "WWW.EPiCS.TOP",
    ]
    assert resp.data["next"] is None

    prev_url = urllib.parse.urlparse(resp.data["previous"])
    assert prev_url.path == "/api/search/servers/"
    assert prev_url.query == "limit=7"

    resp = api_client.get(resp.data["previous"])
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == [
        "-==MYT Team Svr==-",
        "Frosty's Playhouse TSS - VIP",
        "nRg|discord.gg",
        "Sog-team.co.uk Pro!",
        "Frosty's Playhouse TSS - BS",
        "[CN]SWAT4X COOP Server",
        "-==MYT World Svr==-",
    ]
    assert resp.data["previous"] is None

    resp = api_client.get(resp.data["next"])
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == [
        "-==MYT Coop Pro Svr==-",
        "-==MYT Coop Svr==-",
        "WWW.EPiCS.TOP",
    ]


@pytest.mark.parametrize(
    "country, names",
    # fmt: off
    [
        ("GB", ["Sog-team.co.uk Pro!"]),
        ("gb", ["Sog-team.co.uk Pro!"]),
        ("DE", [
            "-==MYT Team Svr==-",
            "[CN]SWAT4X COOP Server",
            "-==MYT World Svr==-",
            "-==MYT Coop Pro Svr==-",
            "-==MYT Coop Svr==-",
            "WWW.EPiCS.TOP",
        ]),
        ("de", [
            "-==MYT Team Svr==-",
            "[CN]SWAT4X COOP Server",
            "-==MYT World Svr==-",
            "-==MYT Coop Pro Svr==-",
            "-==MYT Coop Svr==-",
            "WWW.EPiCS.TOP",
        ]),
        ("US", ["Frosty's Playhouse TSS - VIP", "Frosty's Playhouse TSS - BS"]),
        ("us", ["Frosty's Playhouse TSS - VIP", "Frosty's Playhouse TSS - BS"]),
        ("CY", []),
        ("cy", []),
        ("zz", []),
    ],
    # fmt: on
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_by_country(api_client, country, names):
    resp = api_client.get(f"/api/search/servers/?country={country}")
    assert resp.status_code == 200
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, names",
    # fmt: off
    [
        ("myt", [
            "-==MYT Team Svr==-",
            "-==MYT World Svr==-",
            "-==MYT Coop Pro Svr==-",
            "-==MYT Coop Svr==-",
        ]),
        ("myt team svr", [
            "-==MYT Team Svr==-",
        ]),
        ("myt svr", [
            "-==MYT Team Svr==-",
            "-==MYT World Svr==-",
            "-==MYT Coop Svr==-",
            "-==MYT Coop Pro Svr==-",
        ]),
        ("myt coop", [
            "-==MYT Coop Svr==-",
            "-==MYT Coop Pro Svr==-",
        ]),
        ("sog", [
            "Sog-team.co.uk Pro!",
        ]),
        ("sog team", [
            "Sog-team.co.uk Pro!",
        ]),
        ("sog-team.co.uk", [
            "Sog-team.co.uk Pro!",
        ]),
        ("sog pro", [
            "Sog-team.co.uk Pro!",
        ]),
        ("epics", [
            "WWW.EPiCS.TOP",
        ]),
        ("epics top", [
            "WWW.EPiCS.TOP",
        ]),
        ("wm", []),
    ],
    # fmt: on
    ids=str,
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_by_name(api_client, django_assert_max_num_queries, search_q, names):
    with django_assert_max_num_queries(3):
        resp = api_client.get(f"/api/search/servers/?q={search_q}")
    assert resp.status_code == 200
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, country, names",
    # fmt: off
    [
        ("myt", "us", []),
        ("myt", "de", [
            "-==MYT Team Svr==-",
            "-==MYT World Svr==-",
            "-==MYT Coop Pro Svr==-",
            "-==MYT Coop Svr==-",
        ]),
        ("coop", "gb", []),
        ("coop", "de", [
            "[CN]SWAT4X COOP Server",
            "-==MYT Coop Pro Svr==-",
            "-==MYT Coop Svr==-",
        ]),
    ],
    # fmt: on
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_by_name_and_country(
    api_client, django_assert_max_num_queries, search_q, country, names
):
    with django_assert_max_num_queries(3):
        resp = api_client.get(f"/api/search/servers/?q={search_q}&country={country}")
    assert resp.status_code == 200
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, names",
    # fmt: off
    [
        ("myt team", ["-==MYT Team Svr==-"]),
        ("myt svr", [
            "-==MYT Team Svr==-",
            "-==MYT World Svr==-",
            "-==MYT Coop Svr==-",
            "-==MYT Coop Pro Svr==-",
        ]),
        ("myt coop", [
            "-==MYT Coop Svr==-",
            "-==MYT Coop Pro Svr==-",
        ]),
        ("myt pro", [
            "-==MYT Coop Pro Svr==-",
        ]),
    ],
    # fmt: on
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_relevance(api_client, search_q, names):
    resp = api_client.get(f"/api/search/servers/?q={search_q}")
    assert resp.status_code == 200
    assert [obj["item"]["name_clean"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, headline",
    [
        ("myt", "-==<b>MYT</b> Team Svr==-"),
        ("nrg", "<b>nRg</b>|discord.gg"),
        ("frosty", "<b>Frosty</b>'s Playhouse TSS - VIP"),
        ("vip", "Frosty's Playhouse TSS - <b>VIP</b>"),
        ("coop", "[CN]SWAT4X <b>COOP</b> Server"),
        ("myt team", "-==<b>MYT</b> <b>Team</b> Svr==-"),
        ("sog", "Sog-team.co.uk Pro!"),
    ],
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_search_servers_headline(api_client, search_q, headline):
    resp = api_client.get(f"/api/search/servers/?q={search_q}")
    assert resp.status_code == 200
    first_match = resp.data["results"][0]
    assert first_match["headline"] == headline
    assert first_match["excerpt"] is None
