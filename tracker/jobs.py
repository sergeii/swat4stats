from functools import lru_cache

from django.db.models import Max, Case, When

from tracker.definitions import STAT
from tracker.models import Rank


@lru_cache(maxsize=16)
def get_min_year():
    return 2007


@lru_cache(maxsize=16)
def get_best_kdr(year):
    return (
        Rank.objects
        .filter(year=year)
        .aggregate(
            spm=Max(Case(When(category=STAT.SPM, then='points'))),
            kdr=Max(Case(When(category=STAT.KDR, then='points')))
        )
    )
