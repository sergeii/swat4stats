from typing import Any, ClassVar

from django.contrib import admin
from django.db.models import Count

from apps.tracker.models import Alias, Profile


class AliasInline(admin.TabularInline):
    model = Alias
    fields = ("name", "profile", "isp")
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "alias_count",
        "player_count",
    )
    search_fields = ("name", "alias__name")
    readonly_fields = (
        "loadout",
        "game_first",
        "game_last",
    )
    list_per_page = 20
    inlines: ClassVar[list[admin.TabularInline]] = [AliasInline]

    def earliest_name(self, obj: Profile) -> str:
        return obj.alias_set.first().name

    def latest_name(self, obj: Profile) -> str:
        return obj.alias_set.last().name

    def alias_count(self, obj: Profile) -> int:
        return obj.alias_set.count()

    def player_count(self, obj: Profile) -> int:
        return obj.alias_set.aggregate(num=Count("player"))["num"]

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Do not allow an admin to delete profiles."""
        return False
