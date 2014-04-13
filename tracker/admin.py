# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

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



    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super(IPAdmin, self).get_search_results(request, queryset, search_term)
    #     try:
    #         ip_addr = utils.force_ipy(search_term)
    #         queryset |= queryset.filter(range_from__lte=ip_addr.int(), range_to__gte=ip_addr.int())
    #     except:
    #         pass
    #     return queryset, use_distinct


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
    list_display = ('name', 'ip', 'isp')
    search_fields = ('name', 'ip', 'isp__name')
    readonly_fields = ('isp',)
    list_per_page = 20


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'earliest_name', 'latest_name', 'player_count')
    search_fields = ('name', 'player__name', 'player__ip')
    readonly_fields = ('loadout',)
    list_per_page = 20

    def get_queryset(self, request):
        return super(ProfileAdmin, self).get_queryset(request).annotate(Count('player'))

    def earliest_name(self, obj):
        return obj.player_set.first().name

    def latest_name(self, obj):
        return obj.player_set.last().name

    def player_count(self, obj):
        return obj.player_set.count()
    player_count.admin_order_field = 'player__count'


class PlayerInline(admin.TabularInline):
    model = models.Player
    fields = ('profile', 'loadout', 'vip', 'admin', 'dropped')
    readonly_fields = ('profile', 'loadout', 'vip', 'admin', 'dropped')
    extra = 0


class GameAdmin(admin.ModelAdmin):
    search_fields = ('player__name', 'player__ip')
    list_per_page = 20
    list_display = ('__str__', 'gametype', 'mapname', 'player_num', 'date_finished', 'outcome_readable')
    inlines = (PlayerInline,)

    def outcome_readable(self, obj):
        return shortcuts.map(definitions.stream_pattern_node, 'outcome', force_text(obj.outcome))
    outcome_readable.admin_order_field = 'outcome'


class ScoreInline(admin.TabularInline):
    model = models.Score
    readonly_fields = ('category', 'points')
    extra = 0


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'alias', 'team', 'dropped', 'vip', 'admin')
    readonly_fields = ('game', 'profile', 'alias', 'loadout')
    list_per_page = 20
    inlines = (ScoreInline,)

    def get_queryset(self, request):
        return super(PlayerAdmin, self).get_queryset(request).select_related('profile')


admin.site.register(models.Server)
admin.site.register(models.ServerStatus)
admin.site.register(models.PlayerStatus)
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
admin.site.register(models.Score)
admin.site.register(models.Rank, RankAdmin)