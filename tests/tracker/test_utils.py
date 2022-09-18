import pytest

from tracker.utils import force_clean_name


@pytest.mark.parametrize('name, expected', [
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
])
def test_force_clean_name(name, expected):
    assert force_clean_name(name) == expected
