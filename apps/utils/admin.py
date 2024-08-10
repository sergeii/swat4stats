# ruff: noqa: SLF001
from django.db.models import Model
from django.urls import reverse
from django.utils.html import format_html, format_html_join


def admin_change_url(obj: Model) -> str:
    app_label, model_name = obj._meta.app_label, obj._meta.model_name
    return format_html(
        '<a href="{url}">{obj}</a>',
        url=reverse(f"admin:{app_label}_{model_name}_change", args=(obj.pk,)),
        obj=obj,
    )


def admin_change_urls(objs: list[Model], sep: str = ", ") -> str:
    args_list = (
        (reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=(obj.pk,)), obj)
        for obj in objs
    )
    return format_html_join(sep, '<a href="{}">{}</a>', args_list)
