import urllib.parse
import xml.etree.ElementTree as ET

import pytest

from tracker.factories import GameFactory, ProfileFactory
from tracker.models import Profile


@pytest.mark.parametrize('fields', [
    {},
    {'name': 'Serge', 'country': 'eu'},
    {'team': 0},
    {'name': 'Serge', 'team': 0},
])
def test_unpopular_profile_raises_404(db, client, fields):
    profile = Profile.objects.create(**fields)
    response = client.get(f'/profile/{profile.pk}/')
    assert response.status_code == 404


def test_sitemap_xml(db, client):
    games = GameFactory.create_batch(3, players__batch=5)
    ProfileFactory.create_batch(10, game_first=games[0], game_last=games[-1])

    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/xml'

    root = ET.fromstring(resp.content)
    urls = [c[0].text for c in root]
    sitemaps = {
        urllib.parse.urlparse(u).path for u in urls
    }
    assert sitemaps == {
        '/sitemap-chapters.xml',
        '/sitemap-top-annual.xml',
        '/sitemap-leaderboards-annual.xml',
        '/sitemap-leaderboards-categories.xml',
        '/sitemap-leaderboards-categories-annual.xml',
        '/sitemap-players.xml',
        '/sitemap-games.xml',
    }

    for sub_sitemap in sitemaps:
        resp = client.get(sub_sitemap)
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/xml'
