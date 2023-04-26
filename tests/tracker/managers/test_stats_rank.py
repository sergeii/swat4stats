import pytest
from django.utils import timezone

from apps.tracker.models import PlayerStats, GametypeStats
from apps.tracker.factories import PlayerStatsFactory, ProfileFactory, GametypeStatsFactory


@pytest.mark.django_db(databases=['default', 'replica'])
def test_rank_player_stats():
    now = timezone.now()

    score2016_1 = PlayerStatsFactory(category='score', year=2016, points=100)
    score2016_2 = PlayerStatsFactory(category='score', year=2016, points=10)
    score2016_3 = PlayerStatsFactory(category='score', year=2016, points=1)
    score2015_1 = PlayerStatsFactory(category='score', year=2015, points=100)
    score2015_2 = PlayerStatsFactory(category='score', year=2015, points=10)
    arrests2015 = PlayerStatsFactory(category='arrests', year=2015, points=100)
    killsnow_1 = PlayerStatsFactory(category='kills', year=now.year, points=100)
    killsnow_2 = PlayerStatsFactory(category='kills', year=now.year, points=99)

    def refresh():
        for obj in [score2016_1, score2016_2, score2016_3,
                    score2015_1, score2015_2, arrests2015,
                    killsnow_1, killsnow_2]:
            obj.refresh_from_db()

    PlayerStats.objects.rank(year=now.year)
    refresh()
    assert killsnow_1.position == 1
    assert killsnow_2.position == 2
    assert score2016_3.position is None
    assert score2016_2.position is None
    assert score2016_1.position is None
    assert score2015_2.position is None
    assert score2015_1.position is None
    assert arrests2015.position is None

    PlayerStats.objects.rank(year=2016)
    refresh()
    assert score2016_3.position == 3
    assert score2016_2.position == 2
    assert score2016_1.position == 1
    assert score2015_2.position is None
    assert score2015_1.position is None
    assert arrests2015.position is None

    PlayerStats.objects.rank(year=2015)
    refresh()
    assert score2015_2.position == 2
    assert score2015_1.position == 1
    assert arrests2015.position == 1


@pytest.mark.django_db(databases=['default', 'replica'])
def test_rank_player_stats_include_exclude_cats():
    now = timezone.now()

    score2016_1 = PlayerStatsFactory(category='score', year=2016, points=100)
    score2016_2 = PlayerStatsFactory(category='score', year=2016, points=10)
    score2016_3 = PlayerStatsFactory(category='score', year=2016, points=1)
    score2015_1 = PlayerStatsFactory(category='score', year=2015, points=100)
    score2015_2 = PlayerStatsFactory(category='score', year=2015, points=10)
    arrests2015 = PlayerStatsFactory(category='arrests', year=2015, points=100)
    killsnow_1 = PlayerStatsFactory(category='kills', year=now.year, points=100)
    killsnow_2 = PlayerStatsFactory(category='kills', year=now.year, points=99)
    arrestsnow_1 = PlayerStatsFactory(category='arrests', year=now.year, points=100)
    arrestsnow_2 = PlayerStatsFactory(category='arrests', year=now.year, points=100, position=1)
    arrestsnow_3 = PlayerStatsFactory(category='arrests', year=now.year, points=101)
    scorenow_1 = PlayerStatsFactory(category='score', year=now.year, points=1000)
    scorenow_2 = PlayerStatsFactory(category='score', year=now.year, points=2000)
    timenow_1 = PlayerStatsFactory(category='time', year=now.year, points=3600)
    timenow_2 = PlayerStatsFactory(category='time', year=now.year, points=36000)
    timenow_3 = PlayerStatsFactory(category='time', year=now.year, points=7200)

    def refresh():
        for obj in [score2016_1, score2016_2, score2016_3,
                    score2015_1, score2015_2, arrests2015,
                    scorenow_1, scorenow_2,
                    killsnow_1, killsnow_2,
                    timenow_1, timenow_2, timenow_3,
                    arrestsnow_1, arrestsnow_2, arrestsnow_3]:
            obj.refresh_from_db()

    PlayerStats.objects.rank(year=now.year, cats=['score', 'arrests'])
    refresh()

    assert killsnow_1.position is None
    assert killsnow_2.position is None
    assert timenow_1.position is None
    assert timenow_2.position is None
    assert timenow_3.position is None
    assert scorenow_2.position == 1
    assert scorenow_1.position == 2
    assert arrestsnow_3.position == 1
    assert arrestsnow_1.position == 2
    assert arrestsnow_2.position == 3
    assert score2016_3.position is None
    assert score2016_2.position is None
    assert score2016_1.position is None
    assert score2015_2.position is None
    assert score2015_1.position is None
    assert arrests2015.position is None

    scorenow_2.position = 2
    scorenow_2.save(update_fields=['position'])
    scorenow_1.position = 1
    scorenow_1.save(update_fields=['position'])
    PlayerStats.objects.rank(year=now.year, exclude_cats=['score', 'arrests'])
    refresh()

    assert killsnow_1.position == 1
    assert killsnow_2.position == 2
    assert timenow_1.position == 3
    assert timenow_2.position == 1
    assert timenow_3.position == 2
    assert scorenow_2.position == 2  # not affected
    assert scorenow_1.position == 1  # not affected
    assert arrestsnow_3.position == 1
    assert arrestsnow_1.position == 2
    assert arrestsnow_2.position == 3
    assert score2016_3.position is None
    assert score2016_2.position is None
    assert score2016_1.position is None
    assert score2015_2.position is None
    assert score2015_1.position is None
    assert arrests2015.position is None


@pytest.mark.django_db(databases=['default', 'replica'])
def test_rank_player_stats_qualify():
    now = timezone.now()
    # also check per gametype, per map etc
    profile1, profile2, profile3 = ProfileFactory.create_batch(3)

    time2016_1 = PlayerStatsFactory(category='time', profile=profile1, year=2016, points=10000)
    time2016_2 = PlayerStatsFactory(category='time', profile=profile2, year=2016, points=20)
    spm2016_1 = PlayerStatsFactory(category='spm_ratio', profile=profile1, year=2016, points=5.56, position=2)  # wrong
    spm2016_2 = PlayerStatsFactory(category='spm_ratio', profile=profile2, year=2016, points=3.3, position=1)

    timenow_1 = PlayerStatsFactory(category='time', profile=profile1, year=now.year, points=999)
    timenow_2 = PlayerStatsFactory(category='time', profile=profile2, year=now.year, points=10000, position=1)

    spmnow_1 = PlayerStatsFactory(category='spm_ratio', profile=profile1, year=now.year, points=3.14, position=3)
    spmnow_2 = PlayerStatsFactory(category='spm_ratio', profile=profile2, year=now.year, points=2.72)
    spmnow_3 = PlayerStatsFactory(category='spm_ratio', profile=profile3, year=now.year, points=3.33, position=1)

    sprnow_1 = PlayerStatsFactory(category='spr_ratio', profile=profile1, year=now.year, points=10.8, position=1)
    sprnow_2 = PlayerStatsFactory(category='spr_ratio', profile=profile2, year=now.year, points=9.1, position=2)

    PlayerStats.objects.rank(year=now.year, cats=['spm_ratio'], qualify={'time': 1000})

    for obj in [spmnow_1, spmnow_2, spmnow_3,
                spm2016_1, spm2016_2, time2016_1, time2016_2,
                timenow_1, timenow_2, sprnow_1, sprnow_2]:
        obj.refresh_from_db()

    assert spmnow_1.position is None
    assert spmnow_2.position == 1
    assert spmnow_3.position is None

    assert spm2016_1.position == 2
    assert spm2016_2.position == 1

    assert time2016_1.position is None
    assert time2016_2.position is None
    assert timenow_1.position is None
    assert timenow_2.position == 1
    assert sprnow_1.position == 1
    assert sprnow_2.position == 2


@pytest.mark.django_db(databases=['default', 'replica'])
def test_rank_map_stats_qualify():
    now = timezone.now()
    profile1, profile2, profile3 = ProfileFactory.create_batch(3)

    timevip2016_1 = GametypeStatsFactory(category='time', gametype='VIP Escort',
                                         profile=profile1, year=2016, points=1900)
    timevip2016_2 = GametypeStatsFactory(category='time', gametype='VIP Escort',
                                         profile=profile2, year=2016, points=2500)
    timevip2016_3 = GametypeStatsFactory(category='time', gametype='VIP Escort',
                                         profile=profile3, year=2016, points=10000)

    timerdnow_1 = GametypeStatsFactory(category='time', gametype='Rapid Deployment',
                                       profile=profile1, year=now.year, points=1900)
    timerdnow_2 = GametypeStatsFactory(category='time', gametype='Rapid Deployment',
                                       profile=profile2, year=now.year, points=2500)
    spmrdnow_1 = GametypeStatsFactory(category='spm_ratio', gametype='Rapid Deployment',
                                      profile=profile1, year=now.year, points=18.1, position=2)
    spmrdnow_2 = GametypeStatsFactory(category='spm_ratio', gametype='Rapid Deployment',
                                      profile=profile2, year=now.year, points=5.8, position=1)
    spmrdnow_3 = GametypeStatsFactory(category='spm_ratio', gametype='Rapid Deployment',
                                      profile=profile3, year=now.year, points=1.5, position=3)

    timevipnow_1 = GametypeStatsFactory(category='time', gametype='VIP Escort',
                                        profile=profile1, year=now.year, points=900)
    timevipnow_2 = GametypeStatsFactory(category='time', gametype='VIP Escort',
                                        profile=profile2, year=now.year, points=18900)
    spmvipnow_1 = GametypeStatsFactory(category='spm_ratio', gametype='VIP Escort',
                                       profile=profile1, year=now.year, points=0.5, position=2)
    spmvipnow_2 = GametypeStatsFactory(category='spm_ratio', gametype='VIP Escort',
                                       profile=profile2, year=now.year, points=1.01)
    spmvipnow_3 = GametypeStatsFactory(category='spm_ratio', gametype='VIP Escort',
                                       profile=profile3, year=now.year, points=18.01, position=1)

    GametypeStats.objects.rank(year=now.year, cats=['spm_ratio'], qualify={'time': 1000})

    for obj in [timevip2016_1, timevip2016_2, timevip2016_3,
                timerdnow_1, timerdnow_2,
                spmrdnow_1, spmrdnow_2, spmrdnow_3,
                timevipnow_1, timevipnow_2,
                spmvipnow_1, spmvipnow_2, spmvipnow_3]:
        obj.refresh_from_db()

    assert spmrdnow_1.position == 1
    assert spmrdnow_2.position == 2
    assert spmrdnow_3.position is None

    assert spmvipnow_1.position is None
    assert spmvipnow_2.position == 1
    assert spmvipnow_3.position is None
