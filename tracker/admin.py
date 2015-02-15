# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.db import transaction
from django.db.models import Count
from django.contrib import admin
from django.utils.encoding import force_text

from julia import shortcuts
from django_markdown.admin import MarkdownModelAdmin

from . import models, utils, definitions


class IPAdmin(admin.ModelAdmin):
    search_fields = ('range_from', 'range_to', 'isp__name')
    list_per_page = 20
    list_display = ('range_from_normal', 'range_to_normal', 'length', 'isp', 'date_created', 'is_actual')
    list_filter = ('isp__country',)
    raw_id_fields = ('isp',)

    def get_queryset(self, request):
        return super(IPAdmin, self).get_queryset(request).select_related('isp')


class IPInline(admin.TabularInline):
    model = models.IP
    fields = ('range_from_normal', 'range_to_normal', 'length')
    readonly_fields = fields 
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ISPAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'count')
    search_fields = ('name',)
    list_filter = ('country',)
    list_per_page = 20
    inlines = (IPInline,)

    def get_queryset(self, request):
        return super(ISPAdmin, self).get_queryset(request).annotate(Count('ip'))

    def count(self, obj):
        return obj.ip_set.count()

    count.admin_order_field = 'ip__count'

    def has_delete_permission(self, request, obj=None):
        return False


class AliasInline(admin.TabularInline):
    model = models.Alias
    fields = ('name', 'profile', 'isp')
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'last_seen', 'alias_count', 'player_count',)
    search_fields = ('name', 'alias__name')
    readonly_fields = ('loadout', 'game_first', 'game_last',)
    list_per_page = 20
    inlines = [AliasInline]

    def get_queryset(self, request):
        return (super(ProfileAdmin, self).get_queryset(request))

    def earliest_name(self, obj):
        return obj.alias_set.first().name

    def latest_name(self, obj):
        return obj.alias_set.last().name

    def alias_count(self, obj):
        return obj.alias_set.count()

    def player_count(self, obj):
        return obj.alias_set.aggregate(num=Count('player'))['num']

    def has_delete_permission(self, request, obj=None):
        """Do not allow an admin to delete profiles."""
        return False


class ServerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'enabled', 'listed', 'streamed', 'pinned', 'version')
    list_filter = ('enabled', 'listed', 'streamed', 'pinned', 'version')
    search_fields = ('ip', 'hostname')
    list_per_page = 50

    def has_delete_permission(self, request, obj=None):
        """Do not allow an admin to delete servers."""
        return False


class ArticleAdmin(MarkdownModelAdmin):
    list_display = ('__str__', 'is_published', 'date_published')
    search_fields = ('title', 'text',)
    list_per_page = 20
    date_hierarchy = 'date_published'


admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Profile, ProfileAdmin)
admin.site.register(models.ISP, ISPAdmin)
admin.site.register(models.IP, IPAdmin)
admin.site.register(models.Article, ArticleAdmin)
