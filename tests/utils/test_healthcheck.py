import os
from unittest import mock


@mock.patch.dict(os.environ, {'GIT_RELEASE_SHA': '8de00b9'})
def test_info_ok(client, db):
    response = client.get('/info/')
    assert response.status_code == 200
    body = response.json()
    assert body['release'] == '8de00b9'


def test_info_no_release_ok(client, db):
    response = client.get('/info/')
    assert response.status_code == 200
    body = response.json()
    assert body['release'] is None


def test_healthcheck_ok(client, db):
    response = client.get('/healthcheck/')
    assert response.status_code == 200
    assert response.json() == {
        'database': 'ok',
        'redis': 'ok',
    }
