import random

from cacheback.decorators import cacheback
from django.db.models import Min, Max, Case, When

from tracker.definitions import STAT
from tracker.models import Rank, Profile


@cacheback(lifetime=24 * 3600, fetch_on_miss=True)
def get_min_year():
    return Rank.objects.aggregate(year=Min('year'))['year']


@cacheback(lifetime=24 * 3600, fetch_on_miss=True)
def get_best_kdr(year):
    return (
        Rank.objects
        .filter(year=year)
        .aggregate(
            spm=Max(Case(When(category=STAT.SPM, then='points'))),
            kdr=Max(Case(When(category=STAT.KDR, then='points')))
        )
    )


@cacheback(lifetime=24 * 3600, fetch_on_miss=True)
def get_random_name():
    queryset = Profile.objects.filter(name__isnull = False)
    try:
        profile = queryset[random.randrange(1, queryset.count())]
    except (IndexError, ValueError):
        return None
    return profile.name
