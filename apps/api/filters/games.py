from typing import ClassVar

import django_filters

from apps.tracker.models import Game


class GameFilterSet(django_filters.FilterSet):
    day = django_filters.NumberFilter(field_name="date_finished", lookup_expr="day")
    month = django_filters.NumberFilter(field_name="date_finished", lookup_expr="month")
    year = django_filters.NumberFilter(field_name="date_finished", lookup_expr="year")

    class Meta:
        model = Game
        fields: ClassVar[list[str]] = ["server", "map", "gametype", "day", "month", "year"]
