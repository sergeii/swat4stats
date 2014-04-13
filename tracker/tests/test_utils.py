from __future__ import unicode_literals

import unittest

from mock import patch

from tracker import utils


class ForceNameTestCase(unittest.TestCase):
    known_values = (
        (('', '127.0.0.1'), '_ebbeb00c'),
        (('', '2130706433'), '_ebbeb00c'),
        (('', 2130706433), '_ebbeb00c'),
        ((' ', '127.0.0.1'), '_ebbeb00c'),
        ((' ', '2130706433'), '_ebbeb00c'),
        (('Serge', '127.0.0.1'), 'Serge'),
        ((' ', '77.179.220.97'), '_dc966665'),
        (('', '201.78.244.55'), '_3c8dde09'),
        (('', 1394165668), '_aa548b03'),
        (('', '1394165668'), '_aa548b03'),
        (('', '83.25.71.164'), '_aa548b03'),
        ((r'[c=FFFF00]', '201.78.244.55'), '_3c8dde09'),
        ((r'[b][u] [\u]', '201.78.244.55'), '_3c8dde09'),
    )

    def test_known_values(self):
        for (name, ip), expected in self.known_values:
            self.assertEqual(utils.force_name(name, ip), expected)


class ForceCleanNameTestCase(unittest.TestCase):
    known_values = (
        (r'  Serge  ', 'Serge'),
        (r'[i]Serge[\i]', r'[i]Serge[\i]'),
        (r'[c=FF0000]Serge', 'Serge'),
        (r'[c=F]Serge', 'Serge'),
        (r'[c=]Serge', 'Serge'),
        (r'[c]Serge[\c]', 'Serge'),
        (r' [c=FF0000]Serge', 'Serge'),
        (r'[c=FF0001][u]Serge[b]', 'Serge'),
        (r'[c=FF[u]003[\u]0][u]Serge[b][c=FF00]', 'Serge'),
        (r'[c=FFFF00]', ''),
        (r'[b][u][\u]', ''),
        (r'[b] [u]  [\u] ', ''),
        (r'[c=704070][b]M[c=A080A0]a[c=D0C0D0]i[c=FFFFFF]n', 'Main'),
        (r'[c=F4F4F4][b]Kee[c=E9E9E9]p u[c=DEDEDE]r h[c=D3D3D3]ead[c=C8C8C8] do[c=BDBDBD]wn', 'Keep ur head down'),
    )
    def test_known_values(self):
        for name, expected in self.known_values:
            self.assertEqual(utils.force_clean_name(name), expected)