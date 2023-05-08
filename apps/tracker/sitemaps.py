from django.urls import reverse
from django.contrib import sitemaps

from apps.tracker import models as m
from apps.tracker.managers import ProfileQuerySet, ServerQuerySet


class ServerSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'hourly'

    def items(self) -> ServerQuerySet:
        return m.Server.objects.listed()

    def location(self, obj: m.Server) -> str:
        return reverse('servers:detail', kwargs={'server_ip': obj.ip, 'server_port': obj.port})


class ProfileSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'daily'

    def items(self) -> ProfileQuerySet:
        return m.Profile.objects.played()

    def location(self, obj: m.Profile) -> str:
        kwargs = {'profile_id': obj.pk}
        if obj.name:
            kwargs['slug'] = obj.name
        return reverse('profile:profile', kwargs=kwargs)
