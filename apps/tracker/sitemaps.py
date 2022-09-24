from django.urls import reverse
from django.contrib import sitemaps

from apps.tracker import models
from apps.tracker.templatetags import profile_url, game_url


class ServerSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'always'

    def items(self):
        return models.Server.objects.with_status()

    def location(self, obj):
        return reverse('servers:detail', args=(), kwargs={'server_ip': obj.ip,
                                                          'server_port': obj.port})


class ProfileSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'daily'

    def items(self):
        return models.Profile.objects.played()

    def location(self, obj):
        return profile_url(obj, 'profile:overview')


class GameSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'never'

    def items(self):
        return models.Game.objects.all()

    def location(self, obj):
        return game_url(obj)
