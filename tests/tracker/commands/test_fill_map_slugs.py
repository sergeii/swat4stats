import pytest
from django.core.management import call_command

from tests.factories.tracker import MapFactory


@pytest.mark.django_db(databases=["default", "replica"])
def test_fill_map_slugs(django_assert_num_queries):
    abomb = MapFactory(name="A-Bomb Nightclub", slug="a-bomb-nightclub")
    brewer = MapFactory(name="Brewer County Courthouse", slug=None)
    northside = MapFactory(name="Northside Vending", slug="northside-vending-2")
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse", slug=None)
    new_library = MapFactory(name="New Library", slug="new-library")
    dead_end = MapFactory(name="DEAD_END", slug="dead-end")
    delta = MapFactory(name="DELTA CENTER", slug="delta-center")

    with django_assert_num_queries(3):
        call_command("fill_map_slugs")

    for obj in [abomb, brewer, northside, warehouse, new_library, dead_end, delta]:
        obj.refresh_from_db()

    assert abomb.slug == "a-bomb-nightclub"
    assert brewer.slug == "brewer-county-courthouse"
    assert northside.slug == "northside-vending-2"
    assert warehouse.slug == "exp-stetchkov-warehouse"
    assert new_library.slug == "new-library"
    assert dead_end.slug == "dead-end"
    assert delta.slug == "delta-center"
