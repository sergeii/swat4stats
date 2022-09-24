from django import template
from django.utils.html import mark_safe, escape
import markdown as md

register = template.Library()


@register.filter
def markdown(text, *args, **kwargs):
    return mark_safe(md.markdown(escape(text), *args, **kwargs))
