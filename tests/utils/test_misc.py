from datetime import datetime
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from pytz import UTC

from apps.utils.misc import timestamp


class TimestampTestCase(TestCase):
    known_values = [
        (datetime(1970, 1, 1), 0),
        (datetime(2015, 12, 31, 12, 55, 45), 1451566545),
    ]

    def test_known_values(self):
        for current_date, expected_value in self.known_values:
            with mock.patch.object(timezone, 'now', return_value=current_date.replace(tzinfo=UTC)):
                assert timestamp() == expected_value
