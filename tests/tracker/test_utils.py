from datetime import date, datetime

from apps.tracker.utils import (force_name, force_clean_name,
                                iterate_weeks, iterate_years, iterate_months)


def test_force_name():
    known_values = (
        (('', '127.0.0.1'), '_ebbeb00c'),
        ((' ', '127.0.0.1'), '_ebbeb00c'),
        (('Serge', '127.0.0.1'), 'Serge'),
        ((' ', '77.179.220.97'), '_dc966665'),
        (('', '201.78.244.55'), '_3c8dde09'),
        (('', '83.25.71.164'), '_aa548b03'),
        ((r'[c=FFFF00]', '201.78.244.55'), '_3c8dde09'),
        (('[b][u] [\\u]', '201.78.244.55'), '_3c8dde09'),
    )
    for (name, ip), expected in known_values:
        assert force_name(name, ip) == expected


def test_force_clean_name():
    known_values = (
        (r'  Serge  ', 'Serge'),
        (r'[i]Serge[\i]', r'[i]Serge[\i]'),
        (r'[c=FF0000]Serge', 'Serge'),
        (r'[c=F]Serge', 'Serge'),
        (r'[c=]Serge', 'Serge'),
        (r'[c]Serge[\c]', 'Serge'),
        (r' [c=FF0000]Serge', 'Serge'),
        (r'[c=FF0001][u]Serge[b]', 'Serge'),
        ('[c=FF[u]003[\\u]0][u]Serge[b][c=FF00]', 'Serge'),
        (r'[c=FFFF00]', ''),
        ('[b][u][\\u]', ''),
        ('[b] [u]  [\\u] ', ''),
        (r'[c=704070][b]M[c=A080A0]a[c=D0C0D0]i[c=FFFFFF]n', 'Main'),
        (r'[c=F4F4F4][b]Kee[c=E9E9E9]p u[c=DEDEDE]r h[c=D3D3D3]ead[c=C8C8C8] do[c=BDBDBD]wn', 'Keep ur head down'),
    )
    for name, expected in known_values:
        assert force_clean_name(name) == expected


def test_iterate_weeks():
    test_data = [
        ((date(2016, 5, 1), date(2016, 5, 1)), [date(2016, 4, 25)]),
        ((date(2016, 5, 2), date(2016, 5, 2)), [date(2016, 5, 2)]),
        ((datetime(2016, 4, 29), date(2016, 5, 2)), [date(2016, 4, 25), date(2016, 5, 2)]),
        ((date(2016, 4, 29), date(2016, 5, 14)), [date(2016, 4, 25), date(2016, 5, 2), date(2016, 5, 9)]),
        ((date(2015, 12, 31), date(2016, 1, 4)), [date(2015, 12, 28), date(2016, 1, 4)]),
        ((date(2016, 12, 31), date(2016, 1, 4)), []),
    ]
    for (period_from, period_till), expected in test_data:
        assert list(iterate_weeks(period_from, period_till)) == expected


def test_iterate_years():
    test_data = [
        ((datetime(2016, 5, 1), datetime(2016, 5, 1)), [date(2016, 1, 1)]),
        ((date(2015, 12, 31), date(2016, 1, 1)), [date(2015, 1, 1), date(2016, 1, 1)]),
        ((date(2014, 4, 29), date(2016, 5, 2)), [date(2014, 1, 1), date(2015, 1, 1), date(2016, 1, 1)]),
        ((date(2016, 5, 1), date(2015, 5, 2)), []),
    ]
    for (period_from, period_till), expected in test_data:
        assert list(iterate_years(period_from, period_till)) == expected


def test_iterate_months():
    test_data = [
        ((date(2016, 1, 31), date(2016, 1, 2)), [date(2016, 1, 1)]),
        ((date(2015, 12, 31), date(2016, 1, 20)), [date(2015, 12, 1), date(2016, 1, 1)]),
        ((datetime(2015, 1, 31), datetime(2016, 1, 2)), [date(2015, 1, 1),
                                                         date(2015, 2, 1),
                                                         date(2015, 3, 1),
                                                         date(2015, 4, 1),
                                                         date(2015, 5, 1),
                                                         date(2015, 6, 1),
                                                         date(2015, 7, 1),
                                                         date(2015, 8, 1),
                                                         date(2015, 9, 1),
                                                         date(2015, 10, 1),
                                                         date(2015, 11, 1),
                                                         date(2015, 12, 1),
                                                         date(2016, 1, 1)]),
        ((date(2016, 1, 31), date(2015, 1, 2)), []),
    ]
    for (period_from, period_till), expected in test_data:
        assert list(iterate_months(period_from, period_till)) == expected
