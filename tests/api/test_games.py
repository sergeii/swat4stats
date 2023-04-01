from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytz import UTC

from apps.tracker.factories import (MapFactory, GameFactory,
                                    ServerFactory, PlayerFactory, WeaponFactory)


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
    GameFactory.create_batch(4, server=esa, date_finished=now - timedelta(days=370))  # old games
    GameFactory.create_batch(2, server=soh, date_finished=now - timedelta(days=180))

    resp = api_client.get('/api/data-popular-servers/')
    assert [(obj['id'], obj['name_clean']) for obj in resp.data] == [
        (myt_vip.pk, '-==MYT Team Svr==-'),
        (soh.pk, '|SoH|  Shadow  OF Heroes'),
        (myt_coop.pk, '-==MYT Co-op Svr==-'),
        (esa.pk, '62.21.98.150:9485'),
    ]


def test_get_popular_map_names(db, api_client):
    abomb = MapFactory(name='A-Bomb Nightclub')
    brewer = MapFactory(name='Brewer County Courthouse')
    northside = MapFactory(name='Northside Vending')  # noqa
    warehouse = MapFactory(name='-EXP- Stetchkov Warehouse')
    new_library = MapFactory(name='New Library')
    dead_end = MapFactory(name='DEAD_END')  # noqa

    resp = api_client.get('/api/data-popular-mapnames/')
    # no games
    assert resp.data == []

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


def test_get_games_list(db, api_client):
    resp = api_client.get('/api/games/')
    # no games
    assert resp.data == {
        'next': None,
        'previous': None,
        'results': [],
    }

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

    # pagination
    resp = api_client.get('/api/games/?limit=4')
    assert [obj['id'] for obj in resp.data['results']] == [game6.pk, game5.pk, game4.pk, game3.pk]

    resp = api_client.get(resp.data['next'])
    assert [obj['id'] for obj in resp.data['results']] == [game2.pk, game1.pk]
    assert resp.data['next'] is None

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


def test_get_game_detail(db, api_client):
    resp = api_client.get('/api/games/100500/')
    assert resp.status_code == 404

    server = ServerFactory()
    map = MapFactory(name='A-Bomb Nightclub')

    game = GameFactory(gametype='VIP Escort', map=map, server=server,
                       date_finished=datetime(2017, 1, 1, tzinfo=UTC))
    PlayerFactory.create_batch(11, dropped=False, game=game)

    resp = api_client.get(f'/api/games/{game.pk}/')
    assert resp.status_code == 200
    assert resp.data['map']
    assert resp.data['server']
    assert len(resp.data['players']) == 11
    assert resp.data['coop_rank'] is None

    coop_game = GameFactory(gametype='CO-OP', map=map, server=server,
                            date_finished=datetime(2017, 1, 1, tzinfo=UTC),
                            coop_score=77)
    PlayerFactory.create_batch(5, dropped=False, game=coop_game)
    resp = api_client.get(f'/api/games/{coop_game.pk}/')
    assert resp.status_code == 200
    assert resp.data['map']
    assert resp.data['server']
    assert len(resp.data['players']) == 5
    assert resp.data['coop_rank'] == 'Patrol Officer'


def test_get_game_highlights(db, api_client):
    resp = api_client.get('/api/games/100500/highlights/')
    assert resp.status_code == 404

    # no players game
    game = GameFactory()
    resp = api_client.get(f'/api/games/{game.pk}/highlights/')
    assert resp.status_code == 200
    assert resp.data == []

    # vip game
    game = GameFactory(gametype='VIP Escort')
    dropped = PlayerFactory(game=game, dropped=True,
                            alias__name='Grasz',
                            alias__isp__country='pl')
    WeaponFactory(player=dropped, name='9mm SMG', kills=10, hits=100, shots=100)

    player1 = PlayerFactory(game=game, dropped=False,
                            alias__name='|MYT|dimonkey',
                            alias__isp__country='gb',
                            score=21, kills=21, kill_streak=9, arrest_streak=4, deaths=9)
    WeaponFactory(player=player1, name='9mm SMG', kills=10, hits=100, shots=200)
    WeaponFactory(player=player1, name='9mm Handgun', kills=1, hits=1, shots=2000)

    player2 = PlayerFactory(game=game, dropped=False,
                            alias__name='Pioterator',
                            alias__isp__country='pl',
                            vip=True,
                            score=4, kills=10, teamkills=2, kill_streak=10)
    WeaponFactory(player=player2, name='9mm SMG', hits=1, shots=9999)
    WeaponFactory(player=player2, name='Suppressed 9mm SMG', hits=1, shots=1)
    WeaponFactory(player=player2, name='Flashbang', hits=4, shots=10)
    WeaponFactory(player=player2, name='Stinger', hits=1, shots=10)

    player3 = PlayerFactory(game=game, dropped=False,
                            alias__name='|MYT|Ven>SrM<',
                            score=12, arrests=1, kills=7, deaths=10, kill_streak=5)
    WeaponFactory(player=player3, name='Flashbang', hits=12, shots=5)
    WeaponFactory(player=player3, name='Stinger', hits=0, shots=5)

    player4 = PlayerFactory(game=game, dropped=False,
                            alias__name='|MYT|Q',
                            score=34, arrests=1, kills=4, deaths=12, kill_streak=5, vip_captures=2)
    WeaponFactory(player=player4, name='Colt M4A1 Carbine', kills=10, hits=20, shots=200)
    WeaponFactory(player=player4, name='9mm SMG', kills=1, hits=65, shots=65)

    resp = api_client.get(f'/api/games/{game.pk}/highlights/')
    assert resp.status_code == 200
    hl1, hl2, hl3, hl4, hl5, hl6, hl7 = resp.data

    assert hl1['player']['id'] == player4.pk
    assert hl1['title'] == 'No Exit'
    assert hl1['description'] == '2 VIP captures'

    assert hl2['player']['id'] == player2.pk
    assert hl2['title'] == 'Undying'
    assert hl2['description'] == '10 enemies killed in a row'

    assert hl3['player']['id'] == player4.pk
    assert hl3['title'] == 'Top Gun'
    assert hl3['description'] == '34 points earned'

    assert hl4['player']['id'] == player3.pk
    assert hl4['title'] == 'Fire in the hole!'
    assert hl4['description'] == '100% of grenades hit their targets'

    assert hl5['player']['id'] == player1.pk
    assert hl5['player']['name'] == '|MYT|dimonkey'
    assert hl5['player']['country'] == 'gb'
    assert hl5['player']['country_human'] == 'United Kingdom'
    assert hl5['title'] == 'Killing Machine'
    assert hl5['description'] == '21 enemies eliminated'

    assert hl6['player']['id'] == player2.pk
    assert hl6['title'] == 'Resourceful'
    assert hl6['description'] == '10000 rounds of ammo fired'

    assert hl7['player']['id'] == player1.pk
    assert hl7['title'] == '9mm SMG Expert'
    assert hl7['description'] == '10 kills with average accuracy of 50%'


def test_get_coop_game_highlights(db, api_client):
    game = GameFactory(gametype='CO-OP')
    player1 = PlayerFactory(game=game,
                            alias__name='Mosquito',
                            dropped=False,
                            coop_hostage_arrests=1,
                            coop_enemy_arrests=1,
                            coop_enemy_incaps=5,
                            coop_enemy_kills=4,
                            coop_toc_reports=15)
    player2 = PlayerFactory(game=game,
                            alias__name='|||ALPHA|||boti',
                            dropped=False,
                            coop_hostage_arrests=9,
                            coop_enemy_arrests=8,
                            coop_enemy_incaps=5,
                            coop_toc_reports=12)
    player3 = PlayerFactory(game=game,  # noqa
                            alias__name='Serge',
                            dropped=False,
                            coop_hostage_arrests=6,
                            coop_enemy_arrests=6,
                            coop_enemy_kills=5,
                            coop_toc_reports=14)
    player4 = PlayerFactory(game=game,  # noqa
                            alias__name='Spieler',
                            dropped=True,
                            coop_hostage_arrests=10,
                            coop_toc_reports=17)

    resp = api_client.get(f'/api/games/{game.pk}/highlights/')
    assert resp.status_code == 200
    hl1, hl2, hl3, hl4 = resp.data

    assert hl1['title'] == 'Entry team to TOC!'
    assert hl1['description'] == '15 reports sent to TOC'
    assert hl1['player']['id'] == player1.pk

    assert hl2['title'] == 'Hostage Crisis'
    assert hl2['description'] == '9 civilians rescued'
    assert hl2['player']['id'] == player2.pk

    assert hl3['title'] == 'The pacifist'
    assert hl3['description'] == '8 suspects secured'
    assert hl3['player']['id'] == player2.pk

    assert hl4['title'] == 'No Mercy'
    assert hl4['description'] == '9 suspects neutralized'
    assert hl4['player']['id'] == player1.pk
