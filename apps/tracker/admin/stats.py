from typing import Any

from django.db.models import QuerySet
from django.contrib import admin

from apps.tracker.models import WeaponStats, MapStats, GametypeStats, PlayerStats, ServerStats


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ("profile", "category", "year", "points", "position")
    list_filter = ("category", "year")


@admin.register(WeaponStats)
class WeaponStatsAdmin(admin.ModelAdmin):
    list_display = ("profile", "category", "year", "weapon", "points", "position")
    list_filter = ("weapon", "category", "year")


@admin.register(MapStats)
class MapStatsAdmin(admin.ModelAdmin):
    list_display = ("profile", "category", "year", "map", "points", "position")
    list_filter = (("map", admin.RelatedOnlyFieldListFilter), "category", "year")

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related("map", "profile")


@admin.register(GametypeStats)
class GametypeStatsAdmin(admin.ModelAdmin):
    list_display = ("profile", "category", "year", "gametype", "points", "position")
    list_filter = ("gametype", "category", "year")


@admin.register(ServerStats)
class ServerStatsAdmin(admin.ModelAdmin):
    list_display = ("profile", "category", "year", "server", "points", "position")
    list_filter = (("server", admin.RelatedOnlyFieldListFilter), "category", "year")

    def get_queryset(self, *args: Any, **kwargs: Any) -> QuerySet:
        return super().get_queryset(*args, **kwargs).select_related("server", "profile")
