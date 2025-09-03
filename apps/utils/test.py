from datetime import datetime
from typing import Self
from unittest import mock

from django.utils import timezone


def freeze_timezone_now(dt: datetime) -> mock.patch:
    return mock.patch.object(timezone, "now", return_value=dt)


class FuzzyFloat(float):  # noqa: PLW1641
    precision: int

    def __new__(cls, number: float, precision: int) -> Self:
        obj = super().__new__(cls, number)
        obj.precision = precision
        return obj

    def __eq__(self, other: float | Self) -> bool:
        return round(self, self.precision) == round(other, self.precision)

    def __ne__(self, other: float | Self) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self)

    def __repr__(self) -> str:
        return str(round(self, self.precision))
