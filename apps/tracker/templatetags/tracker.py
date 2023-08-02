from django import template

from apps.tracker.utils.geo import country

__all__ = [
    "country_human",
]

register = template.Library()


@register.filter
def country_human(iso: str | None) -> str:
    return country(iso)
