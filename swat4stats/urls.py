from typing import Any

from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.http import response, HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sitemaps.views import sitemap, index as sitemap_index
from rest_framework import routers

from apps.api.views import (
    ServerViewSet,
    ArticleViewSet,
    PopularMapnamesViewSet,
    PopularServersViewSet,
    GameViewSet,
    ServerLeaderboardViewSet,
    SearchPlayersView,
    SearchServersView,
)
from apps.tracker.sitemaps import ServerSitemap, ProfileSitemap
from apps.tracker.views import APIWhoisView, DataStreamView
from apps.tracker.views.motd import APIMotdLeaderboardView, APILegacySummaryView
from apps.utils.views import healthcheck


def noop(*args: Any, **kwargs: Any) -> HttpResponse:
    return HttpResponse("noop")


sitemaps = {
    "servers": ServerSitemap,
    "players": ProfileSitemap,
}

api_router = routers.DefaultRouter()
api_router.register("servers", ServerViewSet)
api_router.register("games", GameViewSet)
api_router.register("articles", ArticleViewSet)
api_router.register("server-leaderboard", ServerLeaderboardViewSet)
api_router.register("data-popular-mapnames", PopularMapnamesViewSet, basename="popular-mapnames")
api_router.register("data-popular-servers", PopularServersViewSet, basename="popular-servers")

api_urls = [
    path("search/players/", SearchPlayersView.as_view()),
    path("search/servers/", SearchServersView.as_view()),
    path(r"", include(api_router.urls)),
]

urlpatterns = [
    path(
        "sitemap.xml",
        cache_page(3600 * 24)(sitemap_index),
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(3600 * 6)(sitemap),
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
    path("admin/", admin.site.urls),
    # swat server api
    path(
        "api/",
        include(
            [
                path("whois/", APIWhoisView.as_view()),
                path("motd/summary/", APILegacySummaryView.as_view()),
                path("motd/leaderboard/", APIMotdLeaderboardView.as_view()),
                path("motd/leaderboard/<category>/", APIMotdLeaderboardView.as_view()),
            ]
        ),
    ),
    # server stream api view
    path("stream/", csrf_exempt(DataStreamView.as_view()), name="stream"),
    # rest api
    path("api/", include((api_urls, "api"), namespace="api")),
    # noop views, for reverse purposes
    re_path(
        r"^player/(?:(?P<year>\d{4})/)?(?:(?P<slug>[^/]+)/)?(?P<profile_id>\d+)/",
        include(
            (
                [
                    path("", noop, name="profile"),
                    path("overview/", noop, name="overview"),
                ],
                "profile",
            ),
            namespace="profile",
        ),
    ),
    re_path(
        r"^games/(?:(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[^/]+)/)?(?P<game_id>\d+)/",
        include(
            (
                [
                    path("", noop, name="detail"),
                ],
                "games",
            ),
            namespace="games",
        ),
    ),
    re_path(
        r"^servers/(?P<server_ip>[0-9.]+):(?P<server_port>\d{1,5})/",
        include(
            (
                [
                    path("", noop, name="detail"),
                ],
                "servers",
            ),
            namespace="servers",
        ),
    ),
    path("info/", healthcheck.status),
    path("healthcheck/", healthcheck.HealthcheckView.as_view()),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
        *urlpatterns,
    ]


def handler400(*args: Any, **kwargs: Any) -> response.HttpResponseBadRequest:
    return response.HttpResponseBadRequest()


def handler404(*args: Any, **kwargs: Any) -> response.HttpResponseNotFound:
    return response.HttpResponseNotFound()


def handler500(*args: Any, **kwargs: Any) -> response.HttpResponseServerError:
    return response.HttpResponseServerError()
