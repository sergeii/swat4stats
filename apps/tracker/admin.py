from django.core.checks import messages
from django.db.models import Count
from django.contrib import admin
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from apps.tracker.models import (Alias, Profile, Game, Server,
                                 WeaponStats, MapStats, GametypeStats,
                                 PlayerStats, ServerStats)


class AliasInline(admin.TabularInline):
    model = Alias
    fields = ('name', 'profile', 'isp')
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'alias_count', 'player_count',)
    search_fields = ('name', 'alias__name')
    readonly_fields = ('loadout', 'game_first', 'game_last',)
    list_per_page = 20
    inlines = [AliasInline]

    def earliest_name(self, obj):
        return obj.alias_set.first().name

    def latest_name(self, obj):
        return obj.alias_set.last().name

    def alias_count(self, obj):
        return obj.alias_set.count()

    def player_count(self, obj):
        return obj.alias_set.aggregate(num=Count('player'))['num']

    def has_delete_permission(self, *args, **kwargs):
        """Do not allow an admin to delete profiles."""
        return False


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ip', 'port', 'enabled', 'listed', 'pinned', 'version', 'failures')
    list_filter = ('enabled', 'listed', 'pinned', 'version')
    search_fields = ('ip', 'hostname')
    list_per_page = 50
    actions = ['merge_servers']

    def has_delete_permission(self, *args, **kwargs):
        return settings.DEBUG

    @atomic
    def merge_servers(self, request, queryset):
        """
        Merge games to the first server in the queryset.
        """
        if len(queryset) < 2:
            self.message_user(request, _('Too few servers selected'), level=messages.ERROR)
            return
        objects = list(queryset.order_by('pk'))
        target = objects[0]
        servers = objects[1:]
        server_pks = list(map(lambda server: server.pk, servers))
        Game.objects.filter(server__in=server_pks).update(server=target)
        Server.objects.filter(pk__in=server_pks).delete()

    merge_servers.short_description = _('Merge selected servers')


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'year', 'points', 'position')
    list_filter = ('category', 'year')


@admin.register(WeaponStats)
class WeaponStatsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'year', 'weapon', 'points', 'position')
    list_filter = ('weapon', 'category', 'year')


@admin.register(MapStats)
class MapStatsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'year', 'map', 'points', 'position')
    list_filter = (('map', admin.RelatedOnlyFieldListFilter), 'category', 'year')

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related('map', 'profile')


@admin.register(GametypeStats)
class GametypeStatsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'year', 'gametype', 'points', 'position')
    list_filter = ('gametype', 'category', 'year')


@admin.register(ServerStats)
class ServerStatsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'year', 'server', 'points', 'position')
    list_filter = (('server', admin.RelatedOnlyFieldListFilter), 'category', 'year')

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related('server', 'profile')
