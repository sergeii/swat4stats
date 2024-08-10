import urllib.parse
from datetime import datetime
from xml.etree import ElementTree

from pytz import UTC

from tests.factories.query import ServerStatusFactory
from tests.factories.tracker import GameFactory, ProfileFactory, ServerFactory


def test_sitemap_xml(db, client):
    games = GameFactory.create_batch(3, players__batch=5)
    ProfileFactory.create_batch(10, game_first=games[0], game_last=games[-1])
    for _ in range(5):
        ServerFactory(status=ServerStatusFactory())

    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/xml"

    root = ElementTree.fromstring(resp.content)
    urls = [c[0].text for c in root]
    sitemaps = {urllib.parse.urlparse(u).path for u in urls}
    assert sitemaps == {
        "/sitemap-servers.xml",
        "/sitemap-players.xml",
    }


def test_sitemap_servers_xml(db, client, site, django_assert_max_num_queries):
    servers = ServerFactory.create_batch(10, listed=True)
    ServerFactory(listed=False)
    ServerFactory(listed=True, enabled=False)

    with django_assert_max_num_queries(3):
        resp = client.get("/sitemap-servers.xml")

    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/xml"

    root = ElementTree.fromstring(resp.content)
    urls = [c[0].text for c in root]
    assert urls == [f"http://{site.domain}/servers/{s.address}/" for s in servers]


def test_sitemap_players_xml(db, client, site, django_assert_max_num_queries):
    really_long_time_ago = datetime(2010, 1, 18, tzinfo=UTC)
    some_time_ago = datetime(2017, 1, 1, tzinfo=UTC)

    profiles = [
        ProfileFactory(name=name, first_seen_at=really_long_time_ago, last_seen_at=some_time_ago)
        for name in ["John", "Jane", "Joe", "Jill", "Jack", "Jenny", "Jesse"]
    ]

    with django_assert_max_num_queries(3):
        resp = client.get("/sitemap-players.xml")

    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/xml"

    root = ElementTree.fromstring(resp.content)
    urls = {c[0].text for c in root}
    assert urls == {f"http://{site.domain}/player/{p.name}/{p.id}/" for p in profiles}
