from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tracker.models import Map
from tests.factories.tracker import GameFactory, MapFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_popular_map_names(db, api_client):
    now = timezone.now()

    abomb = MapFactory(name="A-Bomb Nightclub")
    brewer = MapFactory(name="Brewer County Courthouse")
    northside = MapFactory(name="Northside Vending")  # noqa: F841
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse")
    new_library = MapFactory(name="New Library")
    dead_end = MapFactory(name="DEAD_END")

    Map.objects.update_ratings()

    resp = api_client.get("/api/data-popular-mapnames/")
    # no games
    assert resp.data == []

    GameFactory.create_batch(3, map=dead_end, date_finished=now - timedelta(days=181))  # old games
    GameFactory.create_batch(3, map=new_library)
    GameFactory(map=abomb)
    GameFactory(map=warehouse)
    GameFactory.create_batch(2, map=brewer)

    Map.objects.update_ratings()

    resp = api_client.get("/api/data-popular-mapnames/")
    assert [(obj["id"], obj["name"]) for obj in resp.data] == [
        (abomb.pk, "A-Bomb Nightclub"),
        (brewer.pk, "Brewer County Courthouse"),
        (warehouse.pk, "-EXP- Stetchkov Warehouse"),
        (new_library.pk, "New Library"),
    ]
