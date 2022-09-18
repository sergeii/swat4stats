import uuid

from tracker.utils import Enum


def test_enum_member_values_are_sequential():
    members = [uuid.uuid4().hex for _ in range(1000)]
    # 1000-member enum
    enum = Enum(*members)

    assert getattr(enum, members[0]) == 0

    x = -1
    for member in members:
        member_value = getattr(enum, member)
        assert member_value-x == 1
        x = member_value
