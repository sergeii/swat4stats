# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.http import response

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('tracker.urls', app_name='tracker', namespace='tracker')),
)


# Return 400, 404 or 500 status codes
# to the frontend without rendering error page templates

def handler400(request, *args, **kwargs):
    return response.HttpResponseBadRequest()

def handler404(request, *args, **kwargs):
    return response.HttpResponseNotFound()

def handler500(request, *args, **kwargs):
    return response.HttpResponseServerError()


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )