from datetime import UTC, datetime

import pytest
from pytest_django.fixtures import DjangoAssertNumQueries, SettingsWrapper

from apps.tracker.tasks import update_map_details
from tests.factories.tracker import MapFactory


@pytest.mark.django_db(databases=["default", "replica"])
@pytest.mark.parametrize(
    "current_sha",
    [
        None,
        "8385df158177793495daf6e44f5fc6d2646079f7",
    ],
)
def test_update_map_details(
    settings: SettingsWrapper,
    django_assert_num_queries: DjangoAssertNumQueries,
    current_sha: str | None,
):
    now = datetime.now(tz=UTC)
    settings.GIT_RELEASE_SHA = "47ac2e2c61a02bf479aa8dbff402ce430472a3fe"

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
        details_updated_for_version=current_sha,
    )

    with django_assert_num_queries(6):
        update_map_details.delay()

    abomb.refresh_from_db()

    assert abomb.preview_picture == "/static/images/maps/preview/a-bomb-nightclub.jpg"
    assert abomb.background_picture == "/static/images/maps/background/a-bomb-nightclub.jpg"
    assert abomb.briefing.startswith("We're being called up for a rapid deployment at ")

    assert abomb.details_updated_at >= now
    assert abomb.details_updated_for_version == "47ac2e2c61a02bf479aa8dbff402ce430472a3fe"


@pytest.mark.django_db(databases=["default", "replica"])
def test_update_map_details_no_sha(
    settings: SettingsWrapper,
    django_assert_num_queries: DjangoAssertNumQueries,
):
    settings.GIT_RELEASE_SHA = None

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
        details_updated_for_version="47ac2e2c61a02bf479aa8dbff402ce430472a3fe",
    )

    with django_assert_num_queries(0):
        update_map_details.delay()

    abomb.refresh_from_db()
    assert abomb.details_updated_at == datetime(2024, 8, 7, 11, 22, 55, tzinfo=UTC)
    assert abomb.details_updated_for_version == "47ac2e2c61a02bf479aa8dbff402ce430472a3fe"
