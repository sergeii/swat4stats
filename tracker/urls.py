from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views import generic

from . import views


def noop(*args, **kwargs):
    return HttpResponse('noop')


profile_urls = [
    path('', views.ProfileDetailView.as_view(), name='profile'),
    path('overview/', views.ProfileDetailView.as_view(), name='profile_overview'),
    path('equipment/', views.ProfileWeaponListView.as_view(), name='profile_equipment'),
    path('coop/', views.ProfileCoopDetailView.as_view(), name='profile_coop'),
    path('ranking/', views.ProfileRankingListView.as_view(), name='profile_ranking'),
    path('history/', views.ProfileHistoryListView.as_view(), name='profile_history'),
]

api_urls = [
    path('motd/summary/', noop),
    re_path(r'^motd/leaderboard/(?:(?P<board_name>\w+)/)?$', noop),
    path('whois/', noop),
]

urlpatterns = [
    # main page
    path('', noop, name='main'),
    # stream page
    path('stream/', noop, name='stream'),
    # stream page
    path('api/', include(api_urls)),
    # profile page
    re_path(
        r'^player/(?:(?P<year>\d{4})/)?(?:(?P<slug>[^/]+)/)?(?P<profile_id>\d+)/',
        include(profile_urls)
    ),
    # legacy profile url redirect page
    re_path(
        r'^player/(?P<name>.+)/$',
        views.ProfileRedirectView.as_view(permanent=True),
        name='player'
    ),
    # top 20
    re_path(r'^top/(?:(?P<year>\d{4})/)?$', views.TopListView.as_view(), name='top'),
    # leaderboards
    re_path(
        r'^leaderboard/(?:(?P<year>\d{4})/)?(?:(?P<board_name>[\w]+)/)?$',
        views.BoardListView.as_view(),
        name='leaderboard'
    ),

    path('games/', noop, name='game_list'),
    path('games/history/',
         generic.RedirectView.as_view(pattern_name='tracker:game_list', permanent=True),
         name='game_list_history'),
    path('games/online/',
         generic.RedirectView.as_view(pattern_name='tracker:game_list', permanent=True),
         name='game_list_online'),
    re_path(
        r'^games/(?:(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[^/]+)/)?(?P<game_id>\d+)/$',
        noop,
        name='game'
    ),
    path('servers/', noop, name='server_list'),
    re_path(
        r'^servers/(?P<server_ip>[0-9.]+):(?P<server_port>\d{1,5})/$',
        noop,
        name='server'
    ),

    # search page
    path('search/', views.PlayerSearchView.as_view(), name='search'),
]
