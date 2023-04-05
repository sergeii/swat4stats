import logging

from IPy import IP

logger = logging.getLogger(__name__)


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


def rank_dicts(dicts):
    best = {}
    for d in dicts:
        for key, value in d.items():
            if key not in best or value > best[key]:
                best[key] = value
    return best


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
