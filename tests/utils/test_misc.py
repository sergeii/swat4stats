from datetime import datetime
from unittest import mock

import pytest
from django.utils import timezone
from pytz import UTC

from apps.utils.misc import timestamp


@pytest.mark.parametrize('current_date, expected', [
    (datetime(1970, 1, 1), 0),
    (datetime(2015, 12, 31, 12, 55, 45), 1451566545),
])
def test_timestamp(current_date, expected):
    with mock.patch.object(timezone, 'now', return_value=current_date.replace(tzinfo=UTC)):
        assert timestamp() == expected
