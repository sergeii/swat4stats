from django.core.checks import messages
from django.db.models import Count
from django.contrib import admin
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from . import models


@admin.register(models.IP)
class IPAdmin(admin.ModelAdmin):
    search_fields = ('range_from', 'range_to', 'isp__name')
    list_per_page = 20
    list_display = ('range_from_normal', 'range_to_normal', 'length', 'isp', 'date_created')
    list_filter = ('isp__country',)
    raw_id_fields = ('isp',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('isp')


class IPInline(admin.TabularInline):
    model = models.IP
    fields = ('range_from_normal', 'range_to_normal', 'length')
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


@admin.register(models.ISP)
class ISPAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'count')
    search_fields = ('name',)
    list_filter = ('country',)
    list_per_page = 20
    inlines = (IPInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(Count('ip'))

    def count(self, obj):
        return obj.ip_set.count()
    count.admin_order_field = 'ip__count'

    def has_delete_permission(self, *args, **kwargs):
        return False


class AliasInline(admin.TabularInline):
    model = models.Alias
    fields = ('name', 'profile', 'isp')
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'last_seen', 'alias_count', 'player_count',)
    search_fields = ('name', 'alias__name')
    readonly_fields = ('loadout', 'game_first', 'game_last',)
    list_per_page = 20
    inlines = [AliasInline]

    def get_queryset(self, request):
        return super().get_queryset(request)

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


@admin.register(models.Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'enabled', 'listed', 'streamed', 'pinned', 'version')
    list_filter = ('enabled', 'listed', 'streamed', 'pinned', 'version')
    search_fields = ('ip', 'hostname')
    list_per_page = 50
    actions = ['merge_servers']

    def has_delete_permission(self, *args, **kwargs):
        return False

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
        server_pks = [server.pk for server in servers]
        models.Game.objects.filter(server__in=server_pks).update(server=target)
        models.Server.objects.filter(pk__in=server_pks).delete()
    merge_servers.short_description = _('Merge selected servers')


@admin.register(models.Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_published', 'date_published')
    search_fields = ('title', 'text',)
    list_per_page = 20
    date_hierarchy = 'date_published'
