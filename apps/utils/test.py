from __future__ import annotations

from unittest import mock

from django.utils import timezone


def freeze_timezone_now(datetime):
    return mock.patch.object(timezone, "now", return_value=datetime)


class FuzzyFloat(float):
    precision: int

    def __new__(cls, number: float, precision: int) -> FuzzyFloat:
        obj = super().__new__(cls, number)
        obj.precision = precision
        return obj

    def __eq__(self, other: float | int | FuzzyFloat) -> bool:
        return round(self, self.precision) == round(other, self.precision)

    def __ne__(self, other: float | int | FuzzyFloat) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return str(round(self, self.precision))
