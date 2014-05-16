# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import six

from django.core.urlresolvers import reverse
from django.contrib import sitemaps

from . import views, models, templatetags


class ViewSitemapMixin(object):
    priority = 0.7
    changefreq = 'daily'

    def location(self, item):
        try:
            view, args, kwargs = item
        except:
            view, args, kwargs = (item, (), {})
        return reverse(view, args=args, kwargs=kwargs)


class StaticViewSitemapMixin(ViewSitemapMixin):
    changefreq = 'weekly'


class AnnualViewSitemapMixin(views.AnnualViewMixin, ViewSitemapMixin):
    priority = 0.5
    changefreq = 'weekly'

    view_name = None

    def items(self):
        items = []
        for year in self.years:
            items.append((self.view_name, (), {'year': year}))
        return items


class LeaderboardCategorySitemap(ViewSitemapMixin, sitemaps.Sitemap):

    def items(self):
        items = []
        for category in six.itervalues(views.BoardListView.get_boards()):
            items.append(('tracker:leaderboard', (), {'board_name': category['name']}))
        return items


class LeaderboardAnnualCategorySitemap(LeaderboardCategorySitemap, AnnualViewSitemapMixin):

    def items(self):
        items = []
        views = super(LeaderboardAnnualCategorySitemap, self).items()
        for year in self.years:
            # copy the list
            for view, args, kwargs in views:
                kwargs = kwargs.copy()
                # only update the year kwarg
                kwargs.update({'year': year})
                items.append((view, args, kwargs))
        return items


class TopAnnualSitemap(AnnualViewSitemapMixin, sitemaps.Sitemap):
    view_name = 'tracker:top'


class LeaderboardAnnualSitemap(AnnualViewSitemapMixin, sitemaps.Sitemap):
    view_name = 'tracker:leaderboard'


class ChapterSitemap(ViewSitemapMixin, sitemaps.Sitemap):
    priority = 1.0
    changefreq = 'hourly'

    def items(self):
        return [
            'tracker:top',
            'tracker:leaderboard',
            'tracker:server_list', 
            'tracker:game_list_history', 
            'tracker:game_list_online',
        ]


class ServerSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'always'

    def items(self):
        return models.Server.objects.status

    def location(self, item):
        kwargs = {'server_ip': item.server.ip, 'server_port': item.server.port}
        return reverse('tracker:server', args=(), kwargs=kwargs)


class ProfileSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'daily'

    def items(self):
        return models.Profile.objects.popular()

    def location(self, obj):
        return templatetags.profile_url(obj, 'tracker:profile')


class GameSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'never'

    def items(self):
        return models.Game.objects.all()

    def location(self, obj):
        return templatetags.game_url(obj)