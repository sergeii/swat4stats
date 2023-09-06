import json
from collections.abc import Iterable, Iterator
from datetime import datetime, time, timedelta
from functools import partial

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.timezone import is_aware
from pytz import UTC


def timestamp():
    """
    Return the current unix timestamp
    """
    return (timezone.now() - datetime(1970, 1, 1, tzinfo=UTC)).total_seconds()


def force_timedelta(value):
    """
    Pass `value` to the timedelta constructor
    as number of seconds unless `value` is a timedelta instance itself
    then return the instance.
    """
    if isinstance(value, timedelta):
        return value
    return timedelta(seconds=int(value))


def force_datetime(maybe_datetime, time_obj=None):
    """
    Convert date object to a UTC datetime
    """
    if isinstance(maybe_datetime, datetime):
        new_datetime = maybe_datetime
        if time_obj:
            new_datetime = datetime.combine(maybe_datetime, time_obj).replace(
                tzinfo=maybe_datetime.tzinfo
            )
        # force tz to UTC
        if not is_aware(new_datetime):
            new_datetime = new_datetime.replace(tzinfo=UTC)
        return new_datetime
    return datetime.combine(maybe_datetime, time_obj or time.min).replace(tzinfo=UTC)


def force_date(maybe_date):
    """
    Convert datetime to date.
    """
    if isinstance(maybe_date, datetime):
        return maybe_date.date()
    return maybe_date


def iterate_queryset(
    queryset: QuerySet, *, fields: list[str], chunk_size: int = 1000
) -> Iterator[list]:
    queryset = queryset.order_by("pk")
    last_pk = 0
    while True:
        chunk = list(queryset.filter(pk__gt=last_pk).values(*fields)[:chunk_size])
        yield chunk
        if len(chunk) < chunk_size:
            break
        last_pk = chunk[-1]["pk"]


def iterate_list(list_: list, *, size: int) -> Iterator[list]:
    for i in range(0, len(list_), size):
        yield list_[i : i + size]


def concat_it(iterable: Iterable, sep: str = ", ") -> str:
    return sep.join(str(item) for item in iterable)


dumps = partial(json.dumps, separators=(",", ":"))
