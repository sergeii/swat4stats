from django.db.models import QuerySet
from django.urls import reverse
from django.contrib import sitemaps
from django.utils.text import slugify

from apps.tracker import models
from apps.tracker.managers import ProfileQuerySet, ServerQuerySet


class ServerSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'always'

    def items(self) -> ServerQuerySet:
        return models.Server.objects.with_status()

    def location(self, obj: models.Server) -> str:
        return reverse('servers:detail', kwargs={'server_ip': obj.ip, 'server_port': obj.port})


class ProfileSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'daily'

    def items(self) -> ProfileQuerySet:
        return models.Profile.objects.played()

    def location(self, obj: models.Profile) -> str:
        kwargs = {'profile_id': obj.pk}
        if obj.name:
            kwargs['slug'] = obj.name
        return reverse('profile:overview', kwargs=kwargs)


class GameSitemap(sitemaps.Sitemap):
    limit = 1000
    changefreq = 'never'

    def items(self) -> QuerySet:
        return models.Game.objects.all()

    def location(self, obj: models.Game) -> str:
        kwargs = {
            'game_id': obj.pk,
            'year': obj.date_finished.strftime('%Y'),
            'month': obj.date_finished.strftime('%m'),
            'day': obj.date_finished.strftime('%d'),
            'slug': slugify(obj.map.name),
        }
        return reverse('games:detail', kwargs=kwargs)
