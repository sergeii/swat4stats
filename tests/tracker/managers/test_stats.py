from datetime import datetime

from pytz import UTC

from apps.tracker.managers.stats import get_stats_period_for_year


def test_period_dates():
    annual_2015 = (
        datetime(2015, 1, 1, tzinfo=UTC),
        datetime(2015, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
    )
    annual_2022 = (
        datetime(2022, 1, 1, tzinfo=UTC),
        datetime(2022, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
    )

    assert get_stats_period_for_year(2015) == annual_2015
    assert get_stats_period_for_year(2022) == annual_2022
