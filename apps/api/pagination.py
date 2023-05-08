from typing import Any

from rest_framework import pagination
from rest_framework.request import Request


class CursorPagination(pagination.CursorPagination):
    ordering = '-pk'
    page_size = 100

    def get_page_size(self, request: Request) -> int:
        default_page_size = super().get_page_size(request)
        try:
            return int(request.GET['limit'])
        except (KeyError, TypeError, ValueError):
            return default_page_size


def paginator_factory(**attrs: Any) -> type[CursorPagination]:
    return type('CustomPaginatonClass', (CursorPagination,), attrs)
