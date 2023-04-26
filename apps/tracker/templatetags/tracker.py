from django import template

from apps.tracker.utils.geo import country

register = template.Library()


@register.filter
def country_human(iso: str | None) -> str:
    return country(iso)
