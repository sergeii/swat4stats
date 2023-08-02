from typing import Any

from rest_framework.filters import OrderingFilter


def ordering_filter_factory(**attrs: Any) -> type[OrderingFilter]:
    return type("CustomOrderingFilter", (OrderingFilter,), attrs)
