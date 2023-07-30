import urllib.parse
from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytz import UTC

from apps.tracker.factories import MapFactory, GameFactory, ServerFactory


@pytest.mark.django_db(databases=['default', 'replica'])
def test_get_popular_servers(db, api_client):
    now = timezone.now()

    myt_coop = ServerFactory(hostname='-==MYT Co-op Svr==-')
    myt_vip = ServerFactory(hostname='-==MYT Team Svr==-')
    esa = ServerFactory(hostname=None, ip='62.21.98.150', port=9485)
    soh = ServerFactory(hostname='[C=F00000] |SoH| [C=FDFDFD] Shadow [C=FF0000] OF Heroes')
    default = ServerFactory(hostname='Swat4 Server')  # noqa

    resp = api_client.get('/api/data-popular-servers/')
    # no games
    assert resp.data == []

    GameFactory.create_batch(3, server=default, date_finished=now - timedelta(days=400))  # old games
    GameFactory.create_batch(3, server=myt_vip)
    GameFactory(server=myt_coop, date_finished=now - timedelta(days=30))
    GameFactory(server=esa)
    GameFactory.create_batch(4, server=esa, date_finished=now - timedelta(days=181))  # old games
    GameFactory.create_batch(2, server=soh, date_finished=now - timedelta(days=179))

    resp = api_client.get('/api/data-popular-servers/')
    assert [(obj['id'], obj['name_clean']) for obj in resp.data] == [
        (myt_vip.pk, '-==MYT Team Svr==-'),
        (soh.pk, '|SoH|  Shadow  OF Heroes'),
        (esa.pk, '62.21.98.150:9485'),
        (myt_coop.pk, '-==MYT Co-op Svr==-'),
    ]


@pytest.mark.django_db(databases=['default', 'replica'])
def test_get_popular_map_names(db, api_client):
    now = timezone.now()

    abomb = MapFactory(name='A-Bomb Nightclub')
    brewer = MapFactory(name='Brewer County Courthouse')
    northside = MapFactory(name='Northside Vending')  # noqa
    warehouse = MapFactory(name='-EXP- Stetchkov Warehouse')
    new_library = MapFactory(name='New Library')
    dead_end = MapFactory(name='DEAD_END')  # noqa

    resp = api_client.get('/api/data-popular-mapnames/')
    # no games
    assert resp.data == []

    GameFactory.create_batch(3, map=dead_end, date_finished=now - timedelta(days=181))  # old games
    GameFactory.create_batch(3, map=new_library)
    GameFactory(map=abomb)
    GameFactory(map=warehouse)
    GameFactory.create_batch(2, map=brewer)

    resp = api_client.get('/api/data-popular-mapnames/')
    assert [(obj['id'], obj['name']) for obj in resp.data] == [
        (abomb.pk, 'A-Bomb Nightclub'),
        (brewer.pk, 'Brewer County Courthouse'),
        (warehouse.pk, '-EXP- Stetchkov Warehouse'),
        (new_library.pk, 'New Library'),
    ]


def test_get_games_list_filters(db, api_client):
    server1, server2 = ServerFactory.create_batch(2)
    abomb = MapFactory(name='A-Bomb Nightclub')
    brewer = MapFactory(name='Brewer County Courthouse')

    game1 = GameFactory(gametype='VIP Escort', map=abomb, server=server1,
                        date_finished=datetime(2017, 1, 1, tzinfo=UTC))
    game2 = GameFactory(gametype='VIP Escort', map=abomb, server=server1,
                        date_finished=datetime(2017, 1, 1, tzinfo=UTC))
    game3 = GameFactory(gametype='Barricaded Suspects', map=brewer, server=server2,
                        date_finished=datetime(2017, 3, 1, tzinfo=UTC))
    game4 = GameFactory(gametype='CO-OP', map=brewer, server=server2,
                        date_finished=datetime(2017, 10, 10, tzinfo=UTC))
    game5 = GameFactory(gametype='Rapid Deployment', map=brewer, server=server1,
                        date_finished=datetime(2016, 1, 1, tzinfo=UTC))
    game6 = GameFactory(gametype='Rapid Deployment', map=abomb, server=server1,
                        date_finished=datetime(2016, 10, 10, tzinfo=UTC))

    resp = api_client.get('/api/games/')
    assert resp.data['next'] is None
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game5.pk, game4.pk,
                                                           game3.pk, game2.pk, game1.pk]

    # filter by map
    resp = api_client.get('/api/games/', {'map': abomb.pk})
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game2.pk, game1.pk]

    resp = api_client.get('/api/games/', {'map': brewer.pk})
    assert [obj['id'] for obj in resp.data['results']] == [game5.pk, game4.pk, game3.pk]

    # filter by gametype
    resp = api_client.get('/api/games/', {'gametype': 'VIP Escort'})
    assert [obj['id'] for obj in resp.data['results']] == [game2.pk, game1.pk]

    resp = api_client.get('/api/games/', {'gametype': 'CO-OP'})
    assert [obj['id'] for obj in resp.data['results']] == [game4.pk]

    # filter by server
    resp = api_client.get('/api/games/', {'server': server1.pk})
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game5.pk, game2.pk, game1.pk]

    # filter by date
    resp = api_client.get('/api/games/', {'day': '1'})
    assert [obj['id'] for obj in resp.data['results']] == [game5.pk, game3.pk, game2.pk, game1.pk]

    resp = api_client.get('/api/games/', {'day': '1', 'month': '1'})
    assert [obj['id'] for obj in resp.data['results']] == [game5.pk, game2.pk, game1.pk]

    resp = api_client.get('/api/games/', {'day': '1', 'month': '1', 'year': '2017'})
    assert [obj['id'] for obj in resp.data['results']] == [game2.pk, game1.pk]

    # filter by map, server, gametype
    resp = api_client.get('/api/games/', {'map': brewer.pk, 'server': server2.pk})
    assert [obj['id'] for obj in resp.data['results']] == [game4.pk, game3.pk]

    resp = api_client.get('/api/games/', {'map': brewer.pk, 'server': server2.pk, 'gametype': 'CO-OP'})
    assert [obj['id'] for obj in resp.data['results']] == [game4.pk]


@pytest.mark.django_db(databases=['default', 'replica'])
def test_get_games_list_pagination(db, api_client):
    game1, game2, game3, game4, game5, game6 = GameFactory.create_batch(6)

    resp = api_client.get('/api/games/?limit=4')
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game5.pk, game4.pk, game3.pk]
    assert resp.data['previous'] is None

    next_url = urllib.parse.urlparse(resp.data['next'])
    assert next_url.path == '/api/games/'
    assert next_url.query.startswith('cursor=')

    resp = api_client.get(resp.data['next'])
    assert [obj['id'] for obj in resp.data['results']] == [game2.pk, game1.pk]
    assert resp.data['next'] is None

    prev_url = urllib.parse.urlparse(resp.data['previous'])
    assert prev_url.path == '/api/games/'
    assert prev_url.query.startswith('cursor=')

    resp = api_client.get(resp.data['previous'])
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game5.pk, game4.pk, game3.pk]
    assert resp.data['previous'] is None


@pytest.mark.django_db(databases=['default', 'replica'])
def test_get_games_list_empty(db, api_client):
    resp = api_client.get('/api/games/')
    # no games
    assert resp.data == {
        'next': None,
        'previous': None,
        'results': [],
    }
