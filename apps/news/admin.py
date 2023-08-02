from django.contrib import admin

from apps.news.models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_published", "date_published")
    search_fields = (
        "title",
        "text",
    )
    list_per_page = 20
    date_hierarchy = "date_published"
