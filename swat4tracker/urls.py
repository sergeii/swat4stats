# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.sitemaps.views import index, sitemap
from django.http import response
from django.views.decorators.cache import cache_page

import tracker.sitemaps

admin.autodiscover()

sitemaps = {
    'chapters': tracker.sitemaps.ChapterSitemap,
    'top-annual': tracker.sitemaps.TopAnnualSitemap,
    'leaderboards-annual': tracker.sitemaps.LeaderboardAnnualSitemap,
    'leaderboards-categories': tracker.sitemaps.LeaderboardCategorySitemap,
    'leaderboards-categories-annual': tracker.sitemaps.LeaderboardAnnualCategorySitemap,
    'servers': tracker.sitemaps.ServerSitemap,
    'players': tracker.sitemaps.ProfileSitemap,
    'games': tracker.sitemaps.GameSitemap,
}

urlpatterns = patterns('',
    # sitemaps
    url(r'^sitemap\.xml$', cache_page(60*60)(index), {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', cache_page(60*60)(sitemap), {'sitemaps': sitemaps}, name='sitemaps'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('tracker.urls', app_name='tracker', namespace='tracker')),
)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )


# Return 400, 404 or 500 status codes
# to the frontend without rendering error page templates

def handler400(request, *args, **kwargs):
    return response.HttpResponseBadRequest()

def handler404(request, *args, **kwargs):
    return response.HttpResponseNotFound()

def handler500(request, *args, **kwargs):
    return response.HttpResponseServerError()