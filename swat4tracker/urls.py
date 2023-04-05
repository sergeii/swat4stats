from django.conf import settings
from django.urls import include, path
from django.http import response

urlpatterns = [
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
