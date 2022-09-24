from django.db.models import Count
from django.contrib import admin

from apps.geoip.models import IP, ISP


@admin.register(IP)
class IPAdmin(admin.ModelAdmin):
    search_fields = ('range_from', 'range_to', 'isp__name')
    list_per_page = 20
    list_display = ('range_from_normal', 'range_to_normal', 'admin_length',
                    'isp', 'date_created', 'admin_is_fresh')
    list_filter = ('isp__country',)
    raw_id_fields = ('isp',)
    readonly_fields = ('range_from_normal', 'range_to_normal', 'admin_length')
    fields = readonly_fields + raw_id_fields + ('range_from', 'range_to')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('isp')


class IPInline(admin.TabularInline):
    model = IP
    fields = ('range_from_normal', 'range_to_normal', 'admin_length', 'admin_is_fresh')
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ISP)
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

    def has_delete_permission(self, request, obj=None):
        return False
