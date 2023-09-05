from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tracker.models import Server
from tests.factories.tracker import GameFactory, ServerFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_popular_servers(db, api_client):
    now = timezone.now()

    myt_coop = ServerFactory(hostname="-==MYT Co-op Svr==-")
    myt_vip = ServerFactory(hostname="-==MYT Team Svr==-")
    esa = ServerFactory(hostname=None, ip="62.21.98.150", port=9485)
    soh = ServerFactory(hostname="[C=F00000] |SoH| [C=FDFDFD] Shadow [C=FF0000] OF Heroes")
    swat = ServerFactory(hostname="Swat4 Server")

    Server.objects.update_ratings()

    resp = api_client.get("/api/data-popular-servers/")
    # no games, no ratings
    assert resp.data == []

    GameFactory.create_batch(3, server=swat, date_finished=now - timedelta(days=200))  # old games
    GameFactory.create_batch(3, server=myt_vip)
    GameFactory(server=myt_coop, date_finished=now - timedelta(days=30))
    GameFactory(server=esa)
    GameFactory.create_batch(4, server=esa, date_finished=now - timedelta(days=91))  # old games
    GameFactory.create_batch(2, server=soh, date_finished=now - timedelta(days=89))

    Server.objects.update_ratings()

    resp = api_client.get("/api/data-popular-servers/")
    assert [(obj["id"], obj["name_clean"]) for obj in resp.data] == [
        (myt_vip.pk, "-==MYT Team Svr==-"),
        (soh.pk, "|SoH|  Shadow  OF Heroes"),
        (esa.pk, "62.21.98.150:9485"),
        (myt_coop.pk, "-==MYT Co-op Svr==-"),
    ]
