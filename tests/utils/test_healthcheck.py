import os
from unittest import mock


@mock.patch.dict(os.environ, {"GIT_RELEASE_SHA": "8de00b9", "GIT_RELEASE_VER": "v1.0.0"})
def test_info_ok(client, db):
    response = client.get("/info/")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "v1.0.0"
    assert body["commit"] == "8de00b9"


def test_info_no_release_ok(client, db):
    response = client.get("/info/")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] is None
    assert body["commit"] is None


def test_healthcheck_ok(client, db):
    response = client.get("/healthcheck/")
    assert response.status_code == 200
    assert response.json() == {
        "database": "ok",
        "redis": "ok",
    }
