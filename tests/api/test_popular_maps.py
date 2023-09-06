import pytest
from rest_framework.test import APIClient

from tests.factories.tracker import MapFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_popular_map_names(api_client: APIClient) -> None:
    brewer = MapFactory(name="Brewer County Courthouse", rating=2)
    abomb = MapFactory(name="A-Bomb Nightclub", rating=1)
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse", rating=3)
    new_library = MapFactory(name="New Library", rating=4)
    MapFactory(name="DEAD_END", rating=None)
    MapFactory(name="Northside Vending", rating=None)

    resp = api_client.get("/api/data-popular-mapnames/")
    assert [(obj["id"], obj["name"]) for obj in resp.data] == [
        (abomb.pk, "A-Bomb Nightclub"),
        (brewer.pk, "Brewer County Courthouse"),
        (warehouse.pk, "-EXP- Stetchkov Warehouse"),
        (new_library.pk, "New Library"),
    ]


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_no_popular_map_names_no_rating(api_client: APIClient) -> None:
    MapFactory.create_batch(5, rating=None)

    resp = api_client.get("/api/data-popular-mapnames/")
    assert resp.status_code == 200
    assert resp.data == []
