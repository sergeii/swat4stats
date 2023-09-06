import os
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="swat4stats.com API",
        default_version="v1",
        description="swat4stats.com REST API documentation",
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


class DocsSchemaView(schema_view):
    permission_classes = (permissions.AllowAny,)
    schema = None

    cache_timeout = 0 if settings.DEBUG else 3600 * 24 * 7
    cache_key_prefix = os.environ.get("GIT_RELEASE_VER", "")

    @method_decorator(gzip_page)
    @method_decorator(cache_page(cache_timeout, key_prefix=cache_key_prefix))
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)
