import re
import logging
import datetime
from contextlib import contextmanager

from IPy import IP

from django.utils import timezone
from django.db import connection


logger = logging.getLogger(__name__)


@contextmanager
def lock(mode, *models):
    """
    Context manager for aquiring a transaction-wide lock on PostgreSQL tables.

    The __init__ method accepts two or more arguments.

    The first argument is always a LOCK mode from the list of the standard lock names
        ACCESS SHARE
        ROW SHARE
        ROW EXCLUSIVE
        SHARE UPDATE EXCLUSIVE
        SHARE
        SHARE ROW EXCLUSIVE
        EXCLUSIVE
        ACCESS EXCLUSIVE

    The subsequent args are list of the models that require a lock.
    """
    tables = [model._meta.db_table for model in models]
    with connection.cursor() as cursor:
        tables_sql = ', '.join(tables)
        logger.debug('locking the tables %s with %s', tables_sql, mode)
        cursor.execute(f'LOCK TABLE {tables_sql} IN {mode} MODE')
        yield cursor


class Rank:

    def __init__(self, ranks, score):
        self.score = int(score)
        self.i = self.title = self.lower = self.upper = None

        for i, (title, min_score) in enumerate(ranks):
            if self.score >= min_score:
                self.i = i
                self.title = title
                self.lower = min_score
            else:
                # update the existing rank's upper bound
                self.upper = min_score
                break

    @property
    def total(self):
        return self.upper

    @property
    def remaining(self):
        return self.upper - self.score

    @property
    def complete(self):
        return self.score

    @property
    def remaining_ratio(self):
        return self.remaining / self.total

    @property
    def complete_ratio(self):
        return self.complete / self.total


def calc_coop_score(procedures):
    """
    Calculate and return overall COOP prcedure score.

    Args:
        procedures - iterable of either tracker.models.Procedure objects or julia.node.ListValueNode nodes
    """
    score = 0
    if procedures:
        for procedure in procedures:
            try:
                procedure.score
            except AttributeError:
                score += procedure['score'].value
            else:
                score += procedure.score
    return score


def calc_accuracy(weapons, interested, min_ammo=None):
    """
    Calculate average accuracy of a list (or any other iterable) of Weapon model instances.

    Args:
        weapons - Weapon instance iterable
        interested - list of weapon ids accuracy should be counted against
        min_ammo - min number of ammo required to calculate accuracy
    """
    hits = 0
    shots = 0
    for weapon in weapons:
        if weapon.name in interested:
            hits += weapon.hits
            shots += weapon.shots
    return int(calc_ratio(hits, shots, min_divisor=min_ammo) * 100)


def calc_ratio(divident, divisor, min_divident=None, min_divisor=None):
    """
    Return quotient result of true division operation for `divident` and `division`

    If either of `min_divident`, `min_divisor` values is greater
    than its corresponding test values, return zero.
    """
    try:
        assert (min_divident is None or divident >= min_divident)
        assert (min_divisor is None or divisor >= min_divisor)
        return divident/divisor
    except (ValueError, TypeError, ZeroDivisionError, AssertionError):
        return 0.0


def force_ipy(ip_address):
    # no conversion is needed
    if isinstance(ip_address, IP):
        return ip_address
    return IP(ip_address)


def force_timedelta(value):
    """
    Pass `value` to the datetime.timedelta constructor
    as number of seconds unless `value` is a timedelta instance itself
    then return the instance.
    """
    if isinstance(value, datetime.timedelta):
        return value
    return datetime.timedelta(seconds=int(value))


def force_clean_name(name):
    """Return a name free of SWAT text tags and leading/trailing whitespace."""
    while True:
        match = re.search(r'(\[[\\/]?[cub]\]|\[c=[^\[\]]*?\])', name, flags=re.I)
        if not match:
            break
        name = name.replace(match.group(1), '')
    return name.strip()


def sort_key(*comparable):
    def key(player):
        stats = []
        for prop in comparable:
            sign = 1
            if prop.startswith('-'):
                sign = -1
                prop = prop[1:]
            stats.append(getattr(player, prop) * sign)
        return stats
    return key


def rank_dicts(dicts):
    best = {}
    for d in dicts:
        for key, value in d.items():
            if key not in best or value > best[key]:
                best[key] = value
    return best


def today():
    return timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)


def Enum(*sequential, **named):
    """
    Create an enumeration.

    >>> Numbers = Enum('ZERO', 'ONE', 'TWO')
    >>> Numbers.ZERO
    0
    >>> Numbers.ONE
    1

    Credits http://stackoverflow.com/a/1695250
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
