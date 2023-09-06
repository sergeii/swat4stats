import pytest
from rest_framework.test import APIClient

from tests.factories.tracker import ServerFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_popular_servers(api_client: APIClient) -> None:
    myt_coop = ServerFactory(hostname="-==MYT Co-op Svr==-", rating=4)
    myt_vip = ServerFactory(hostname="-==MYT Team Svr==-", rating=1)
    esa = ServerFactory(hostname=None, ip="62.21.98.150", port=9485, rating=3)
    soh = ServerFactory(
        hostname="[C=F00000] |SoH| [C=FDFDFD] Shadow [C=FF0000] OF Heroes",
        rating=2,
    )
    ServerFactory(hostname="Swat4 Server")

    resp = api_client.get("/api/data-popular-servers/")
    assert [(obj["id"], obj["name_clean"]) for obj in resp.data] == [
        (myt_vip.pk, "-==MYT Team Svr==-"),
        (soh.pk, "|SoH|  Shadow  OF Heroes"),
        (esa.pk, "62.21.98.150:9485"),
        (myt_coop.pk, "-==MYT Co-op Svr==-"),
    ]


@pytest.mark.django_db(databases=["default", "replica"])
def test_get_no_popular_servers_no_rating(api_client: APIClient) -> None:
    ServerFactory.create_batch(5, rating=None)

    resp = api_client.get("/api/data-popular-servers/")

    assert resp.status_code == 200
    assert resp.data == []
