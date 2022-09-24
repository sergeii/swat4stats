import unittest
import uuid

from apps.utils.enum import Enum


class EnumTestCase(unittest.TestCase):

    def setUp(self):
        self.members = [str(uuid.uuid4()) for _ in range(1000)]
        # 1000-member enum
        self.enum = Enum(*self.members)

    def test_enums_begin_with_zero(self):
        assert getattr(self.enum, self.members[0]) == 0

    def test_enum_member_values_are_sequential(self):
        x = -1
        for member in self.members:
            member_value = getattr(self.enum, member)
            assert member_value-x == 1
            x = member_value
