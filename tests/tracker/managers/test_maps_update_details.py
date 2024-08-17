from datetime import UTC, datetime

import pytest
from pytest_django import DjangoAssertNumQueries

from apps.tracker.models import Map
from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import MapFactory


@pytest.mark.parametrize(
    "chunk_size, expected_queries",
    [
        (2, 16),
        (10, 6),
        (100, 6),
    ],
)
@pytest.mark.django_db(databases=["default", "replica"])
def test_update_map_details(
    django_assert_num_queries: DjangoAssertNumQueries,
    chunk_size: int,
    expected_queries: int,
) -> None:
    # has briefing, pictures referencing the old filename
    abomb = MapFactory(
        name="A-Bomb Nightclub",
        slug="a-bomb-nightclub",
        preview_picture="/static/images/maps/preview/a-bomb.jpg",
        background_picture="/static/images/maps/background/a-bomb.jpg",
        briefing=(
            "We're being called up for a rapid deployment at "
            "an ongoing shots fired situation at the A-Bomb nightclub."
        ),
        details_updated_for_version="0.9",
        details_updated_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    # has pictures referencing the default filename, no briefing
    brewer = MapFactory(
        name="Brewer County Courthouse",
        slug="brewer-county-courthouse",
        preview_picture="/static/images/maps/preview/intro.jpg",
        background_picture="/static/images/maps/background/intro.jpg",
    )
    # has no briefing, pictures referencing the default filename
    # but this map has already been updated for the latest version
    northside = MapFactory(
        name="Northside Vending",
        slug="northside-vending",
        preview_picture="/static/images/maps/preview/intro.jpg",
        background_picture="/static/images/maps/background/intro.jpg",
        details_updated_at=datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC),
        details_updated_for_version="1.0.0",
    )
    # has no pictures and no slug and no briefing
    fairfax = MapFactory(name="Fairfax Residence", slug=None)
    # has neither pictures nor briefing, but the pictures and briefing are available
    warehouse = MapFactory(name="-EXP- Stetchkov Warehouse", slug="exp-stetchkov-warehouse")
    # has no pictures and no briefing, none are available
    new_library = MapFactory(name="New Library", slug="new-library")
    # has no pictures and no briefing, background_picture is empty for some reason
    delta = MapFactory(
        name="DELTA CENTER",
        slug="delta-center",
        preview_picture="/static/images/maps/preview/intro.jpg",
        background_picture=None,
    )

    with (
        freeze_timezone_now(datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)),
        django_assert_num_queries(expected_queries),
    ):
        Map.objects.update_details(version="1.0.0", chunk_size=chunk_size)

    for obj in [abomb, brewer, northside, fairfax, warehouse, new_library, delta]:
        obj.refresh_from_db()

    assert abomb.preview_picture == "/static/images/maps/preview/a-bomb-nightclub.jpg"
    assert abomb.background_picture == "/static/images/maps/background/a-bomb-nightclub.jpg"
    assert abomb.briefing.startswith("We're being called up for a rapid deployment at ")
    assert abomb.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert abomb.details_updated_for_version == "1.0.0"

    assert brewer.preview_picture == "/static/images/maps/preview/brewer-county-courthouse.jpg"
    assert (
        brewer.background_picture == "/static/images/maps/background/brewer-county-courthouse.jpg"
    )
    assert brewer.briefing is None
    assert brewer.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert brewer.details_updated_for_version == "1.0.0"

    assert northside.preview_picture == "/static/images/maps/preview/intro.jpg"
    assert northside.background_picture == "/static/images/maps/background/intro.jpg"
    assert northside.briefing is None
    assert northside.details_updated_at == datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC)
    assert northside.details_updated_for_version == "1.0.0"

    assert fairfax.preview_picture == "/static/images/maps/preview/intro.jpg"
    assert fairfax.background_picture == "/static/images/maps/background/intro.jpg"
    assert fairfax.briefing is None
    assert fairfax.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert fairfax.details_updated_for_version == "1.0.0"

    assert warehouse.preview_picture == "/static/images/maps/preview/exp-stetchkov-warehouse.jpg"
    assert (
        warehouse.background_picture == "/static/images/maps/background/exp-stetchkov-warehouse.jpg"
    )
    assert warehouse.briefing.startswith("Okay, listen up. I know you're tired but we have one")
    assert warehouse.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert warehouse.details_updated_for_version == "1.0.0"

    assert new_library.preview_picture == "/static/images/maps/preview/intro.jpg"
    assert new_library.background_picture == "/static/images/maps/background/intro.jpg"
    assert new_library.briefing is None
    assert new_library.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert new_library.details_updated_for_version == "1.0.0"

    assert delta.preview_picture == "/static/images/maps/preview/intro.jpg"
    assert delta.background_picture == "/static/images/maps/background/intro.jpg"
    assert delta.briefing is None
    assert delta.details_updated_at == datetime(2024, 8, 17, 14, 1, 39, tzinfo=UTC)
    assert delta.details_updated_for_version == "1.0.0"


@pytest.mark.parametrize("chunk_size", [1, 10, 100])
@pytest.mark.django_db(databases=["default", "replica"])
def test_nothing_to_update(
    django_assert_num_queries: DjangoAssertNumQueries,
    chunk_size: int,
) -> None:
    abomb = MapFactory(
        name="A-Bomb Nightclub",
        slug="a-bomb-nightclub",
        preview_picture="/static/images/maps/preview/a-bomb.jpg",
        background_picture="/static/images/maps/background/a-bomb.jpg",
        briefing=(
            "We're being called up for a rapid deployment at "
            "an ongoing shots fired situation at the A-Bomb nightclub."
        ),
        details_updated_at=datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC),
        details_updated_for_version="1.0.0",
    )
    northside = MapFactory(
        name="Northside Vending",
        slug="northside-vending",
        preview_picture="/static/images/maps/preview/intro.jpg",
        background_picture="/static/images/maps/background/intro.jpg",
        details_updated_at=datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC),
        details_updated_for_version="1.0.0",
    )
    delta = MapFactory(
        name="DELTA CENTER",
        slug="delta-center",
        preview_picture=None,
        background_picture=None,
        briefing=None,
        details_updated_at=datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC),
        details_updated_for_version="1.0.0",
    )

    with django_assert_num_queries(1):
        Map.objects.update_details(version="1.0.0", chunk_size=chunk_size)

    for obj in [abomb, northside, delta]:
        obj.refresh_from_db()
        assert obj.details_updated_at == datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC)
        assert obj.details_updated_for_version == "1.0.0"
