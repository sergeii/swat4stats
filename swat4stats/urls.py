from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.http import response, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sitemaps.views import sitemap, index as sitemap_index
from rest_framework import routers

from apps.api.views import (ServerViewSet, ArticleViewSet,
                            PopularMapnamesViewSet, PopularServersViewSet,
                            GameViewSet, ServerLeaderboardViewSet)
from apps.tracker.sitemaps import ServerSitemap, ProfileSitemap, GameSitemap
from apps.tracker.views import APIWhoisView, DataStreamView
from apps.tracker.views.motd import APIMotdLeaderboardView, APILegacySummaryView


def noop(*args, **kwargs):
    return HttpResponse('noop')


sitemaps = {
    'servers': ServerSitemap,
    'players': ProfileSitemap,
    'games': GameSitemap,
}

api_router = routers.DefaultRouter()
api_router.register(r'servers', ServerViewSet)
api_router.register(r'games', GameViewSet)
api_router.register(r'articles', ArticleViewSet)
api_router.register(r'server-leaderboard', ServerLeaderboardViewSet)
api_router.register(r'data-popular-mapnames', PopularMapnamesViewSet, basename='popular-mapnames')
api_router.register(r'data-popular-servers', PopularServersViewSet, basename='popular-servers')

api_urls = [
    path(r'', include(api_router.urls)),
]

urlpatterns = [
    path('sitemap.xml', sitemap_index, {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    re_path(r'^sitemap-(?P<section>.+)\.xml$', sitemap, {'sitemaps': sitemaps}, name='sitemaps'),
    path('admin/', admin.site.urls),

    # swat server api
    path('api/', include([
        path('whois/', APIWhoisView.as_view()),
        path('motd/summary/', APILegacySummaryView.as_view()),
        path('motd/leaderboard/', APIMotdLeaderboardView.as_view()),
        path('motd/leaderboard/<category>/', APIMotdLeaderboardView.as_view()),
    ])),
    # server stream api view
    path('stream/', csrf_exempt(DataStreamView.as_view()), name='stream'),

    # rest api
    path('api/', include((api_urls, 'api'), namespace='api')),

    # noop views, for reverse purposes
    re_path(
        r'^player/(?:(?P<year>\d{4})/)?(?:(?P<slug>[^/]+)/)?(?P<profile_id>\d+)/',
        include(([
            path('', noop, name='profile'),
            path('overview/', noop, name='overview'),
        ], 'profile'), namespace='profile')
    ),
    re_path(
        r'^games/(?:(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[^/]+)/)?(?P<game_id>\d+)/',
        include(([
            path('', noop, name='detail'),
        ], 'games'), namespace='games')
    ),
    re_path(
        r'^servers/(?P<server_ip>[0-9.]+):(?P<server_port>\d{1,5})/',
        include(([
            path('', noop, name='detail'),
        ], 'servers'), namespace='servers')
    ),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns


def handler400(request, *args, **kwargs):
    return response.HttpResponseBadRequest()


def handler404(request, *args, **kwargs):
    return response.HttpResponseNotFound()


def handler500(request, *args, **kwargs):
    return response.HttpResponseServerError()