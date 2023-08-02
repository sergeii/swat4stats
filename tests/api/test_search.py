import urllib.parse

import pytest
from django.utils import timezone

from apps.tracker.factories import ProfileFactory, AliasFactory


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture(autouse=True)
def _setup_profiles(db, now):
    today = now
    yesterday = now - timezone.timedelta(days=1)
    two_days_ago = now - timezone.timedelta(days=2)
    three_days_ago = now - timezone.timedelta(days=3)
    four_days_ago = now - timezone.timedelta(days=4)

    tracer = ProfileFactory(name="OW|Tracer", country="GB", last_seen_at=four_days_ago)
    AliasFactory(profile=tracer, name="OW|Tracer", isp__country="GB")
    AliasFactory(profile=tracer, name="Tracer", isp__country="GB")
    # duplicate on purpose
    AliasFactory(profile=tracer, name="Tracer", isp__country="GB")
    AliasFactory(profile=tracer, name="<OW>Tracer", isp__country="GB")

    hanzo = ProfileFactory(name="OW|Hanzo", country="JP", last_seen_at=today)
    AliasFactory(profile=hanzo, name="OW|Hanzo", isp__country="JP")

    genji = ProfileFactory(name="Genji", country="JP", last_seen_at=yesterday)
    AliasFactory(profile=genji, name="Genji", isp__country="JP")
    AliasFactory(profile=genji, name="Mercy_Heal_Me", isp__country="JP")

    winston = ProfileFactory(name="OW|Winston", country="GB", last_seen_at=two_days_ago)
    AliasFactory(profile=winston, name="OW|Winston", isp__country="GB")
    AliasFactory(profile=winston, name="WinstonTheScientist", isp__country="GB")

    widowmaker = ProfileFactory(name="Widowmaker", country="FR", last_seen_at=three_days_ago)
    AliasFactory(profile=widowmaker, name="Widowmaker", isp__country="FR")

    mercy = ProfileFactory(name="OW|Mercy", country="CH", last_seen_at=four_days_ago)
    AliasFactory(profile=mercy, name="OW|Mercy", isp__country="CH")

    bastion = ProfileFactory(name="Bastion", country=None, last_seen_at=None)
    AliasFactory(profile=bastion, name="Bastion", isp__country=None)

    t_racer = ProfileFactory(name="T-racer", country="GB", last_seen_at=yesterday)
    AliasFactory(profile=t_racer, name="T-racer", isp__country="GB")
    AliasFactory(profile=t_racer, name="Tracer", isp__country="GB")

    churchill = ProfileFactory(name="WinstonChurchill", country="GB", last_seen_at=four_days_ago)
    AliasFactory(profile=churchill, name="WinstonChurchill", isp__country="GB")

    winston123 = ProfileFactory(name="Winston123", country="BE", last_seen_at=four_days_ago)
    AliasFactory(profile=winston123, name="Winston123", isp__country="BE")

    winstoned = ProfileFactory(name="Winstoned", country="GB", last_seen_at=four_days_ago)
    AliasFactory(profile=winstoned, name="Winstoned", isp__country="GB")

    thrall = ProfileFactory(name="|WOW|Thrall", country="US", last_seen_at=four_days_ago)
    AliasFactory(profile=thrall, name="|WOW|Thrall", isp__country="US")


def test_search_no_filters(db, api_client, django_assert_max_num_queries):
    with django_assert_max_num_queries(3):
        resp = api_client.get("/api/search/")

    assert resp.status_code == 200

    assert resp.data["previous"] is None
    assert resp.data["next"] is None

    names = [obj["item"]["name"] for obj in resp.data["results"]]
    assert names == [
        "OW|Hanzo",
        "Genji",
        "T-racer",
        "OW|Winston",
        "Widowmaker",
        "OW|Tracer",
        "OW|Mercy",
        "WinstonChurchill",
        "Winston123",
        "Winstoned",
        "|WOW|Thrall",
    ]


@pytest.mark.parametrize(
    "query_params, expected_names",
    [
        # default ordering
        (
            {},
            [
                "OW|Hanzo",
                "Genji",
                "T-racer",
                "OW|Winston",
                "Widowmaker",
                "OW|Tracer",
                "OW|Mercy",
                "WinstonChurchill",
                "Winston123",
                "Winstoned",
                "|WOW|Thrall",
            ],
        ),
        # ordering by last seen desc
        (
            {"ordering": "-last_seen_at"},
            [
                "OW|Hanzo",
                "Genji",
                "T-racer",
                "OW|Winston",
                "Widowmaker",
                "OW|Tracer",
                "OW|Mercy",
                "WinstonChurchill",
                "Winston123",
                "Winstoned",
                "|WOW|Thrall",
            ],
        ),
        # ordering by last seen asc
        (
            {"ordering": "last_seen_at"},
            [
                "OW|Tracer",
                "OW|Mercy",
                "WinstonChurchill",
                "Winston123",
                "Winstoned",
                "|WOW|Thrall",
                "Widowmaker",
                "OW|Winston",
                "Genji",
                "T-racer",
                "OW|Hanzo",
            ],
        ),
        # ordering by last seen asc, limit applied
        ({"ordering": "last_seen_at", "limit": 3}, ["OW|Tracer", "OW|Mercy", "WinstonChurchill"]),
        # ordering by last seen desc, limit applied
        ({"ordering": "-last_seen_at", "limit": 3}, ["OW|Hanzo", "Genji", "T-racer"]),
        # order by last seen, filter by country
        (
            {"ordering": "last_seen_at", "country": "GB"},
            ["OW|Tracer", "WinstonChurchill", "Winstoned", "OW|Winston", "T-racer"],
        ),
        # search by name, order by last seen desc
        (
            {"ordering": "-last_seen_at", "q": "winston"},
            ["OW|Winston", "WinstonChurchill", "Winston123"],
        ),
        # search by name, order by last seen asc
        (
            {"ordering": "last_seen_at", "q": "winston"},
            ["OW|Winston", "WinstonChurchill", "Winston123"],
        ),
    ],
)
def test_search_ordering(db, api_client, query_params, expected_names):
    resp = api_client.get("/api/search/", query_params)
    assert resp.status_code == 200
    names = [obj["item"]["name"] for obj in resp.data["results"]]
    assert names == expected_names


def test_search_pagination_no_filters(db, api_client):
    resp = api_client.get("/api/search/?limit=7")

    assert resp.status_code == 200

    assert resp.data["previous"] is None
    assert [obj["item"]["name"] for obj in resp.data["results"]] == [
        "OW|Hanzo",
        "Genji",
        "T-racer",
        "OW|Winston",
        "Widowmaker",
        "OW|Tracer",
        "OW|Mercy",
    ]

    next_url = urllib.parse.urlparse(resp.data["next"])
    assert next_url.path == "/api/search/"
    assert next_url.query == "limit=7&offset=7"

    resp = api_client.get(resp.data["next"])
    assert [obj["item"]["name"] for obj in resp.data["results"]] == [
        "WinstonChurchill",
        "Winston123",
        "Winstoned",
        "|WOW|Thrall",
    ]
    assert resp.data["next"] is None

    prev_url = urllib.parse.urlparse(resp.data["previous"])
    assert prev_url.path == "/api/search/"
    assert prev_url.query == "limit=7"

    resp = api_client.get(resp.data["previous"])
    assert [obj["item"]["name"] for obj in resp.data["results"]] == [
        "OW|Hanzo",
        "Genji",
        "T-racer",
        "OW|Winston",
        "Widowmaker",
        "OW|Tracer",
        "OW|Mercy",
    ]
    assert resp.data["previous"] is None

    resp = api_client.get(resp.data["next"])
    assert [obj["item"]["name"] for obj in resp.data["results"]] == [
        "WinstonChurchill",
        "Winston123",
        "Winstoned",
        "|WOW|Thrall",
    ]


@pytest.mark.parametrize(
    "country, names",
    [
        ("GB", ["T-racer", "OW|Winston", "OW|Tracer", "WinstonChurchill", "Winstoned"]),
        ("gb", ["T-racer", "OW|Winston", "OW|Tracer", "WinstonChurchill", "Winstoned"]),
        ("JP", ["OW|Hanzo", "Genji"]),
        ("jp", ["OW|Hanzo", "Genji"]),
        ("FR", ["Widowmaker"]),
        ("fr", ["Widowmaker"]),
        ("CH", ["OW|Mercy"]),
        ("ch", ["OW|Mercy"]),
        ("CY", []),
        ("cy", []),
        ("zz", []),
    ],
)
def test_search_by_country(db, api_client, country, names):
    resp = api_client.get(f"/api/search/?country={country}")
    assert resp.status_code == 200
    assert [obj["item"]["name"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, names",
    [
        ("Roadhog", []),
        ("t racer", ["T-racer"]),
        ("t Racer", ["T-racer"]),
        ("Tracer", ["OW|Tracer", "T-racer"]),
        ("tracer", ["OW|Tracer", "T-racer"]),
        ("ow tracer", ["OW|Tracer"]),
        ("ow", ["OW|Hanzo", "OW|Winston", "OW|Tracer", "OW|Mercy"]),
        ("winston", ["OW|Winston", "WinstonChurchill", "Winston123"]),
        ("Churchill", ["WinstonChurchill"]),
        ("Church", []),
        ("Mercy", ["OW|Mercy", "Genji"]),
        ("Mercy Heal Me", ["Genji"]),
    ],
)
def test_search_by_name(db, api_client, django_assert_max_num_queries, search_q, names):
    with django_assert_max_num_queries(3):
        resp = api_client.get(f"/api/search/?q={search_q}")
    assert resp.status_code == 200
    assert [obj["item"]["name"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, country, names",
    [
        ("Roadhog", "us", []),
        ("Tracer", "gb", ["OW|Tracer", "T-racer"]),
        ("tracer", "gb", ["OW|Tracer", "T-racer"]),
        ("ow tracer", "gb", ["OW|Tracer"]),
        ("ow", "gb", ["OW|Winston", "OW|Tracer"]),
        ("winston", "gb", ["OW|Winston", "WinstonChurchill"]),
        ("ow", "us", []),
        ("wow", "us", ["|WOW|Thrall"]),
    ],
)
def test_search_by_name_and_country(
    db, api_client, django_assert_max_num_queries, search_q, country, names
):
    with django_assert_max_num_queries(3):
        resp = api_client.get(f"/api/search/?q={search_q}&country={country}")
    assert resp.status_code == 200
    assert [obj["item"]["name"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, names",
    [
        ("Mercy", ["OW|Mercy", "Genji"]),
        ("Tracer", ["OW|Tracer", "T-racer"]),
    ],
)
def test_search_relevance(db, api_client, search_q, names):
    resp = api_client.get(f"/api/search/?q={search_q}")
    assert resp.status_code == 200
    assert [obj["item"]["name"] for obj in resp.data["results"]] == names


@pytest.mark.parametrize(
    "search_q, headline, excerpt",
    [
        ("tracer", "OW|<b>Tracer</b>", "<b>Tracer</b>"),
        ("OW|Tracer", "<b>OW</b>|<b>Tracer</b>", None),
        ("Tracer ow", "<b>OW</b>|<b>Tracer</b>", None),
        ("|OW|Tracer", "<b>OW</b>|<b>Tracer</b>", None),
        ("ow tracer", "<b>OW</b>|<b>Tracer</b>", None),
        ("t racer", "T-<b>racer</b>", None),
        ("mercy", "OW|<b>Mercy</b>", None),
        ("winston", "OW|<b>Winston</b>", "WinstonTheScientist"),
        ("scientist", "OW|Winston", "WinstonTheScientist"),
        ("WinstonTheScientist", "OW|Winston", "<b>WinstonTheScientist</b>"),
    ],
)
def test_search_headline(db, api_client, search_q, headline, excerpt):
    resp = api_client.get(f"/api/search/?q={search_q}")
    assert resp.status_code == 200
    first_match = resp.data["results"][0]
    assert first_match["headline"] == headline
    assert first_match["excerpt"] == excerpt
