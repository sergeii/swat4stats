# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.conf.urls import include, url
from django.views import generic

from . import views

profile_urls = [
    url(r'^$', views.ProfileDetailView.as_view(), name='profile'),
    url(r'^overview/$', views.ProfileDetailView.as_view(), name='profile_overview'),
    url(r'^equipment/$', views.ProfileWeaponListView.as_view(), name='profile_equipment'),
    url(r'^coop/$', views.ProfileCoopDetailView.as_view(), name='profile_coop'),
    url(r'^ranking/$', views.ProfileRankingListView.as_view(), name='profile_ranking'),
    url(r'^history/$', views.ProfileHistoryListView.as_view(), name='profile_history'),
]

api_urls = [
    url(r'^motd/summary/$', views.APIMotdSummaryView.as_view()),
    url(r'^motd/leaderboard/(?:(?P<board_name>[\w]+)/)?$', views.APIMotdLeaderboardView.as_view()),
    url(r'^whois/$', views.APIWhoisView.as_view()),
]

urlpatterns = [
    # main page
    url(r'^$', views.MainView.as_view(), name='main'),
    # stream page
    url(r'^stream/$', views.StreamView.as_view(), name='stream'),
    # stream page
    url(r'^api/', include(api_urls)),
    # profile page
    url(
        r'^player/(?:(?P<year>\d{4})/)?(?:(?P<slug>[^/]+)/)?(?P<profile_id>\d+)/', 
        include(profile_urls)
    ),
    # legacy profile url redirect page
    url(
        r'^player/(?P<name>.+)/$',
        views.ProfileRedirectView.as_view(permanent=True),
        name='player'
    ),
    # top 20
    url(r'^top/(?:(?P<year>\d{4})/)?$', views.TopListView.as_view(), name='top'),
    # leaderboards
    url(
        r'^leaderboard/(?:(?P<year>\d{4})/)?(?:(?P<board_name>[\w]+)/)?$', 
        views.BoardListView.as_view(), 
        name='leaderboard'
    ),

    url(
        r'^games/$',
        generic.RedirectView.as_view(pattern_name='tracker:game_list_history', permanent=True),
        name='game_list'
    ),
    url(r'^games/history/$', views.GameListView.as_view(), name='game_list_history'),
    url(r'^games/online/$', views.GameOnlineListView.as_view(), name='game_list_online'),
    url(
        r'^games/(?:(?P<slug_year>\d{4})/(?P<slug_month>\d{2})/(?P<slug_day>\d{2})/(?P<slug_name>[^/]+)/)?(?P<game_id>\d+)/$', 
        views.GameDetailView.as_view(),
        name='game'
    ),
    url(r'^servers/$', views.ServerListView.as_view(), name='server_list'),
    url(r'^servers/(?P<server_ip>[0-9.]+):(?P<server_port>\d{1,5})/$', views.ServerDetailView.as_view(), name='server'),

    # search page
    url(r'^search/$', views.PlayerSearchView.as_view(), name='search'),
]
