import pytest
from django.test import Client
from pytest_django.fixtures import SettingsWrapper


@pytest.mark.django_db
def test_info_ok(client: Client, settings: SettingsWrapper) -> None:
    settings.GIT_RELEASE_SHA = "8de00b9"
    settings.GIT_RELEASE_VER = "v1.0.0"

    response = client.get("/info/")
    assert response.status_code == 200

    body = response.json()
    assert body["version"] == "v1.0.0"
    assert body["commit"] == "8de00b9"


@pytest.mark.django_db
def test_info_no_release_ok(client: Client) -> None:
    response = client.get("/info/")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] is None
    assert body["commit"] is None


@pytest.mark.django_db
def test_healthcheck_ok(client: Client) -> None:
    response = client.get("/healthcheck/")
    assert response.status_code == 200
    assert response.json() == {
        "database": "ok",
        "redis": "ok",
    }
