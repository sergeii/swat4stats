# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.db import transaction
from django.db.models import Count
from django.contrib import admin
from django.utils.encoding import force_text
from julia import shortcuts

from . import models, utils, definitions


class RankAdmin(admin.ModelAdmin):
    ordering = ('-points',)
    list_per_page = 30
    raw_id_fields = ('profile',)
    search_fields = ('profile__name',)
    list_filter = ('category', 'year')
    list_display = ('position', 'category', 'year', 'profile', 'points',)


class LoadoutAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'count')
    list_per_page = 20

    def count(self, obj):
        return obj.player_set.count()
    count.admin_order_field = 'player__count'

    def get_queryset(self, request):
        return super(LoadoutAdmin, self).get_queryset(request).annotate(Count('player'))


class IPAdmin(admin.ModelAdmin):
    search_fields = ('range_from', 'range_to', 'isp__name')
    list_per_page = 20
    list_display = ('range_from_normal', 'range_to_normal', 'length', 'isp', 'date_created', 'is_actual')
    list_filter = ('isp__country',)

    def get_queryset(self, request):
        return super(IPAdmin, self).get_queryset(request).select_related('isp')


class IPInline(admin.TabularInline):
    model = models.IP
    fields = ('range_from_normal', 'range_to_normal', 'length')
    readonly_fields = fields 
    extra = 0


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


class AliasAdmin(admin.ModelAdmin):
    list_display = ('name', 'isp')
    search_fields = ('name', 'isp__name')
    readonly_fields = ('profile', 'isp',)
    list_per_page = 20


class AliasInline(admin.TabularInline):
    model = models.Alias
    fields = ('name', 'profile', 'isp')
    readonly_fields = ('profile', 'isp',)
    extra = 0


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


class PlayerInline(admin.TabularInline):
    model = models.Player
    fields = ('alias', 'loadout', 'vip', 'admin', 'dropped')
    readonly_fields = ('alias', 'loadout', 'vip', 'admin', 'dropped')
    extra = 0


class GameAdmin(admin.ModelAdmin):
    search_fields = ('player__alias__name', 'player__ip')
    list_per_page = 20
    list_display = ('__str__', 'gametype', 'mapname', 'player_num', 'date_finished', 'outcome_readable')
    inlines = (PlayerInline,)

    def outcome_readable(self, obj):
        return shortcuts.map(definitions.stream_pattern_node, 'outcome', force_text(obj.outcome))
    outcome_readable.admin_order_field = 'outcome'


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'alias', 'team', 'dropped', 'vip', 'admin')
    readonly_fields = ('game', 'alias', 'loadout')
    list_per_page = 20

    def get_queryset(self, request):
        return super(PlayerAdmin, self).get_queryset(request).select_related('profile')


class ServerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'enabled', 'listed', 'streamed')
    list_filter = ('enabled', 'listed', 'streamed')
    search_fields = ('ip',)
    list_per_page = 50


admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Alias, AliasAdmin)
admin.site.register(models.Profile, ProfileAdmin)
admin.site.register(models.Game, GameAdmin)
admin.site.register(models.Player, PlayerAdmin)
admin.site.register(models.Loadout, LoadoutAdmin)
admin.site.register(models.Weapon)
admin.site.register(models.ISP, ISPAdmin)
admin.site.register(models.IP, IPAdmin)
admin.site.register(models.Procedure)
admin.site.register(models.Objective)
admin.site.register(models.Rank, RankAdmin)