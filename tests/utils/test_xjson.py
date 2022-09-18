from datetime import datetime, date

from django.utils import timezone
from pytz import UTC

from utils import xjson


def test_datetime_encoder():
    xjson_utc_string = '{"__type__": "__datetime__", "isoformat": "2016-05-02T09:22:11+00:00"}'
    assert xjson.loads(xjson_utc_string) == datetime(2016, 5, 2, 9, 22, 11, tzinfo=UTC)

    xjson_naive_string = '{"__type__": "__datetime__", "isoformat": "2016-05-02T09:22:11"}'
    assert xjson.dumps(datetime(2016, 5, 2, 9, 22, 11)) == xjson_naive_string
    assert xjson.loads(xjson_naive_string) == datetime(2016, 5, 2, 9, 22, 11)

    now = timezone.now()
    assert xjson.loads(xjson.dumps({'dates': [now]})) == {'dates': [now]}

    xjson_micro_string = '{"__type__": "__datetime__", "isoformat": "2016-05-02T09:22:11.012221"}'
    assert xjson.dumps(datetime(2016, 5, 2, 9, 22, 11, 12221)) == xjson_micro_string
    assert xjson.loads(xjson_micro_string) == datetime(2016, 5, 2, 9, 22, 11, 12221)


def test_date_encoder():
    today = date.today()

    assert xjson.loads(xjson.dumps(today)) == today
    assert xjson.loads(xjson.dumps([today])) == [today]
    assert xjson.loads(xjson.dumps({'dates': {'today': today}})) == {'dates': {'today': today}}

    assert xjson.dumps(date(2016, 5, 2)) == '{"__type__": "__date__", "isoformat": "2016-05-02"}'
    assert xjson.loads('{"__type__": "__date__", "isoformat": "2016-05-02"}') == date(2016, 5, 2)


def test_regression_tests():
    for value in [0, 1, 1.1, '1', '1.1', [1], [], True, False]:
        assert xjson.loads(xjson.dumps(value)) == value

    assert xjson.loads(xjson.dumps(None)) is None
    assert xjson.loads(xjson.dumps((1, 2, 3))) == [1, 2, 3]
