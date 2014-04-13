# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.conf.urls import patterns, include, url

from . import views


profile_urls = patterns('',
    url(r'^$', views.ProfileDetailView.as_view(), name='profile_detail'),
    url(r'^equipment/$', views.ProfileWeaponListView.as_view(), name='profile_equipment_list'),
    url(r'^coop/$', views.ProfileCoopDetailView.as_view(), name='profile_coop_detail'),
    url(r'^history/$', views.ProfileHistoryListView.as_view(), name='profile_history_list'),
)

urlpatterns = patterns('',
    url(r'^$', views.MainView.as_view(), name='main'),
    # profile page
    url(
        r'^player/(?:(?P<slug>[^/]+)/)?(?P<profile_id>\d+)/(?:(?P<year>\d{4})/)?', 
        include(profile_urls)
    ),
    # top 20
    url(
        r'^top/(?:(?P<year>\d{4})/)?$', 
        views.TopListView.as_view(),
         name='top_list'
    ),
    # leaderboards
    url(
        r'^leaderboard/(?:(?P<board_name>[\w]+)/)?(?:(?P<year>\d{4})/)?$', 
        views.BoardListView.as_view(), 
        name='board_list'
    ),

    url(r'^games/$', views.GameListView.as_view(), name='game_list'),
    url(r'^games/history/$', views.GameListView.as_view(), name='game_history_list'),

    url(r'^servers/$', views.ServerListView.as_view(), name='server_list'),
    url(r'^servers/(?P<server_ip>[0-9.]+):(?P<server_port>\d{1,5})/$', views.ServerDetailView.as_view(), name='server_detail'),
    #url(r'^games/online/$', views.GameOnlineListView.as_view(), name='game_online_list'),

    url(r'^games/(?:(?P<slug>.+)/)?(?P<game_id>\d+)/$', views.GameDetailView.as_view(), name='game_detail'),
    url(r'^stream/$', views.StreamView.as_view(), name='stream'),
)