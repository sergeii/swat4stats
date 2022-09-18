from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.contrib.sitemaps.views import index, sitemap
from django.http import response
from django.views.decorators.cache import cache_page

from tracker import sitemaps as sm


sitemaps = {
    'chapters': sm.ChapterSitemap,
    'top-annual': sm.TopAnnualSitemap,
    'leaderboards-annual': sm.LeaderboardAnnualSitemap,
    'leaderboards-categories': sm.LeaderboardCategorySitemap,
    'leaderboards-categories-annual': sm.LeaderboardAnnualCategorySitemap,
    'players': sm.ProfileSitemap,
    'games': sm.GameSitemap,
}

urlpatterns = [
    # sitemaps
    path('sitemap.xml', cache_page(60*60)(index), {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    re_path(r'^sitemap-(?P<section>.+)\.xml$', cache_page(60*60)(sitemap), {'sitemaps': sitemaps}, name='sitemaps'),
    path('admin/', admin.site.urls),
    path('', include(('tracker.urls', 'tracker'), namespace='tracker')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]


def handler400(request, *args, **kwargs):
    return response.HttpResponseBadRequest()


def handler404(request, *args, **kwargs):
    return response.HttpResponseNotFound()


def handler500(request, *args, **kwargs):
    return response.HttpResponseServerError()
