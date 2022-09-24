from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4, UUID

from django.utils import timezone
from pytz import UTC

from apps.utils import xjson


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


def test_uuid_encoder():
    uuid = uuid4()

    assert xjson.loads(xjson.dumps(uuid)) == uuid
    assert xjson.loads(xjson.dumps([uuid])) == [uuid]
    assert xjson.loads(xjson.dumps({'objs': {'uid': uuid}})) == {'objs': {'uid': uuid}}

    assert xjson.dumps(
        UUID('a1c242c9-e16f-4211-81ee-d5cd01cea013')
    ) == '{"__type__": "__uuid__", "uuid": "a1c242c9-e16f-4211-81ee-d5cd01cea013"}'
    uuid_loaded = xjson.loads('{"__type__": "__uuid__", "uuid": "a1c242c9-e16f-4211-81ee-d5cd01cea013"}')
    assert isinstance(uuid_loaded, UUID)
    assert uuid_loaded == UUID('a1c242c9-e16f-4211-81ee-d5cd01cea013')


def test_decimal_encoder():
    pi = Decimal('3.14')

    assert xjson.loads(xjson.dumps(pi)) == pi
    assert xjson.loads(xjson.dumps([pi])) == [pi]
    assert xjson.loads(xjson.dumps({'numbers': {'pi': pi}})) == {'numbers': {'pi': pi}}

    assert xjson.dumps(pi) == '{"__type__": "__decimal__", "decimal": "3.14"}'
    pi_loaded = xjson.loads('{"__type__": "__decimal__", "decimal": "3.14"}')
    assert isinstance(pi_loaded, Decimal)
    assert pi_loaded == pi


def test_regression_tests():
    for value in [0, 1, 1.1, '1', '1.1', [1], [], True, False]:
        assert xjson.loads(xjson.dumps(value)) == value

    assert xjson.loads(xjson.dumps(None)) is None
    assert xjson.loads(xjson.dumps((1, 2, 3))) == [1, 2, 3]
