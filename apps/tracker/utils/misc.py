import re
import hashlib
import logging
from ipaddress import IPv4Address

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils import html, timezone

from apps.utils.misc import force_date

logger = logging.getLogger(__name__)


def ratio(dividend: int | float,
          divisor: int | float,
          min_dividend: int | float | None = None,
          min_divisor: int | float | None = None) -> float:

    if min_dividend is not None and dividend is not None and dividend < min_dividend:
        return 0.0

    if min_divisor is not None and divisor is not None and divisor < min_divisor:
        return 0.0

    try:
        return dividend / divisor
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def force_clean_name(name: str) -> str:
    """Return a name free of SWAT text tags and leading/trailing whitespace."""
    while True:
        if not (match := re.search(r'(\[[\\/]?[cub]\]|\[c[^\w][^\[\]]*?\])', name, flags=re.I)):
            break
        name = name.replace(match.group(1), '')
    return name.strip()


def force_valid_name(name: str, ip_address: str) -> str:
    """
    Enforce name for given name, ip address pair.

    If provided name is empty, return the 8 to 16 characters of the sha1 hash
    derived from the numeric form of the provided IP address.

    Otherwise, return the provided name as is.
    """
    if not name:
        numeric_ip = force_bytes(str(int(IPv4Address(ip_address))))
        return f'_{hashlib.sha1(numeric_ip).hexdigest()[8:16]}'
    return name


def force_name(name: str, ip_address: str) -> str:
    """Return a non-empty tagless name."""
    return force_valid_name(force_clean_name(name), ip_address)


def format_name(name: str) -> str:
    name = html.escape(name)
    # replace [c=xxxxxx] tags with html span tags
    name = re.sub(
        r'\[c[^\w]([a-f0-9]{6})\](.*?)(?=\[c[^\w]([a-f0-9]{6})\]|\[\\c\]|$)',
        r'<span style="color:#\1;">\2</span>',
        name,
        flags=re.I
    )
    # remove [b], [\b], [u], [\u], [\c] tags
    name = re.sub(r'\[(?:\\)?[buc]\]', '', name, flags=re.I)
    return html.mark_safe(name)


def iterate_years(start_date, end_date):
    end_date = force_date(end_date)
    year_day = force_date(start_date).replace(day=1, month=1)
    while True:
        if year_day > end_date:
            break
        yield year_day
        year_day += relativedelta(years=1)


def get_current_stat_year() -> int:
    now = timezone.now()
    if now.month == 1 and now.day <= settings.TRACKER_MIN_YEAR_DAY:
        return now.year - 1
    return now.year
