import urllib.parse
import xml.etree.ElementTree as ET

from apps.tracker.factories import GameFactory, ProfileFactory, ServerFactory, ServerStatusFactory


def test_sitemap_xml(db, client):
    games = GameFactory.create_batch(3, players__batch=5)
    ProfileFactory.create_batch(10, game_first=games[0], game_last=games[-1])
    for _ in range(5):
        ServerFactory(status=ServerStatusFactory())

    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/xml'

    root = ET.fromstring(resp.content)
    urls = [c[0].text for c in root]
    sitemaps = {
        urllib.parse.urlparse(u).path for u in urls
    }
    assert sitemaps == {
        '/sitemap-servers.xml',
        '/sitemap-players.xml',
        '/sitemap-games.xml',
    }

    for sub_sitemap in sitemaps:
        resp = client.get(sub_sitemap)
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/xml'
