from django.core.management import call_command

from apps.tracker.factories import PlayerStatsFactory


def test_convert_stats(db):
    ps1 = PlayerStatsFactory(category='score', category_legacy=0, year=2016, points=100)
    ps2 = PlayerStatsFactory(category=None, category_legacy=0, year=2016, points=10)
    ps3 = PlayerStatsFactory(category=None, category_legacy=0, year=2016, points=1)
    ps4 = PlayerStatsFactory(category='score', category_legacy=0, year=2015, points=100)
    ps5 = PlayerStatsFactory(category='score', year=2015, points=10)
    ps6 = PlayerStatsFactory(category=None, category_legacy=7, year=2015, points=100)
    ps7 = PlayerStatsFactory(category='kills', category_legacy=0, year=2023, points=100)  # mapping is wrong
    ps8 = PlayerStatsFactory(category=None, category_legacy=6, year=2023, points=99)

    call_command('convert_stats')

    for ps in [ps1, ps2, ps3, ps4, ps5, ps6, ps7, ps8]:
        ps.refresh_from_db()

    assert ps1.category == 'score'
    assert ps1.category_legacy == 0

    assert ps2.category == 'score'
    assert ps2.category_legacy == 0

    assert ps3.category == 'score'
    assert ps3.category_legacy == 0

    assert ps4.category == 'score'
    assert ps4.category_legacy == 0

    assert ps5.category == 'score'
    assert ps5.category_legacy == 0

    assert ps6.category == 'arrests'
    assert ps6.category_legacy == 7

    # mapping is wrong on purpose
    # to test that not null values are not overwritten
    assert ps7.category == 'kills'
    assert ps7.category_legacy == 0

    assert ps8.category == 'kills'
    assert ps8.category_legacy == 6
