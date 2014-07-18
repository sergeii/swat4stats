from __future__ import unicode_literals

import unittest
import uuid

from django.utils.encoding import force_text
from mock import patch
import six

from tracker import utils, definitions


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
        (('[b][u] [\\u]', '201.78.244.55'), '_3c8dde09'),
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
        ('[c=FF[u]003[\\u]0][u]Serge[b][c=FF00]', 'Serge'),
        (r'[c=FFFF00]', ''),
        ('[b][u][\\u]', ''),
        ('[b] [u]  [\\u] ', ''),
        (r'[c=704070][b]M[c=A080A0]a[c=D0C0D0]i[c=FFFFFF]n', 'Main'),
        (r'[c=F4F4F4][b]Kee[c=E9E9E9]p u[c=DEDEDE]r h[c=D3D3D3]ead[c=C8C8C8] do[c=BDBDBD]wn', 'Keep ur head down'),
    )
    def test_known_values(self):
        for name, expected in self.known_values:
            self.assertEqual(utils.force_clean_name(name), expected)


class EnumTestCase(unittest.TestCase):

    def setUp(self):
        self.members = [force_text(uuid.uuid4()) for _ in six.moves.range(1000)]
        # 1000-member enum
        self.enum = utils.Enum(*self.members)

    def test_enums_begin_with_zero(self):
        self.assertEqual(getattr(self.enum, self.members[0]), 0)

    def test_enum_member_values_are_sequential(self):
        x = -1
        for member in self.members:
            member_value = getattr(self.enum, member)
            self.assertEqual(member_value-x, 1)
            x = member_value


class StatEnumTestCase(unittest.TestCase):

    stats = {
        'SCORE': 0,
        'TIME': 1,
        'GAMES': 2,
        'WINS': 3,
        'LOSSES': 4,
        'DRAWS': 5,
        # good stats
        'KILLS': 6,
        'ARRESTS': 7,
        # bad stats
        'DEATHS': 8,
        'ARRESTED': 9,
        'TEAMKILLS': 10,
        # top stats
        'TOP_SCORE': 11,
        'KILL_STREAK': 12,
        'ARREST_STREAK': 13,
        'DEATH_STREAK': 14,
        # mode specific stats
        'VIP_ESCAPES': 15,
        'VIP_CAPTURES': 16,
        'VIP_RESCUES': 17,
        'VIP_KILLS_VALID': 18,
        'VIP_KILLS_INVALID': 19,
        'VIP_TIMES': 20,
        'RD_BOMBS_DEFUSED': 21,
        'SG_ESCAPES': 22,
        'SG_KILLS': 23,
        # ratio stats
        'SPM': 24,
        'SPR': 25,
        'KDR': 26,

        'COOP_GAMES': 27,
        'COOP_TIME': 28,
        'COOP_WINS': 29,
        'COOP_LOSSES': 30,
        'COOP_HOSTAGE_ARRESTS': 31,
        'COOP_HOSTAGE_HITS': 32,
        'COOP_HOSTAGE_INCAPS': 33,
        'COOP_HOSTAGE_KILLS': 34,
        'COOP_ENEMY_ARRESTS': 35,
        'COOP_ENEMY_HITS': 36,
        'COOP_ENEMY_INCAPS': 37,
        'COOP_ENEMY_KILLS': 38,
        'COOP_ENEMY_INCAPS_INVALID': 39,
        'COOP_ENEMY_KILLS_INVALID': 40,
        'COOP_TOC_REPORTS': 41,
        'COOP_SCORE': 42,
        'COOP_TEAMKILLS': 43,
        'COOP_DEATHS': 44,

        'SUICIDES': 45,
        'TOP_KILLS': 46,
        'TOP_ARRESTS': 47,
        'AMMO_SHOTS': 48,
        'AMMO_HITS': 49,
        'AMMO_ACCURACY': 50,
        'AMMO_DISTANCE': 51,

        'BS_SCORE': 52,
        'BS_TIME': 53,
        'VIP_SCORE': 54,
        'VIP_TIME': 55,
        'RD_SCORE': 56,
        'RD_TIME': 57,
        'SG_SCORE': 58,
        'SG_TIME': 59,
    }

    def test_stat_enum_members_are_in_correct_order(self):
        for name, value in six.iteritems(self.stats):
            self.assertEqual(getattr(definitions.STAT, name), value)
