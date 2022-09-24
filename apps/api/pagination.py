from rest_framework import pagination


class CursorPagination(pagination.CursorPagination):
    ordering = '-pk'
    page_size = 100

    def get_page_size(self, request):
        default_page_size = super().get_page_size(request)
        try:
            return int(request.GET['limit'])
        except (KeyError, TypeError, ValueError):
            return default_page_size


def paginator_factory(**attrs):
    return type('CustomPaginatonClass', (CursorPagination,), attrs)
