from functools import lru_cache

import django_countries
from django import template
from django.contrib.staticfiles.finders import find as find_staticfile
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

register = template.Library()
trans = _


@register.simple_tag
def game_url(game, view='games:detail', **kwargs):
    kwargs.update({
        'game_id': game.pk,
        'year': game.date_finished.strftime('%Y'),
        'month': game.date_finished.strftime('%m'),
        'day': game.date_finished.strftime('%d'),
        'slug': slugify(game.map.name),
    })
    return reverse(view, kwargs=kwargs)


@register.simple_tag
def profile_url(profile, view='profile:overview', **kwargs):
    kwargs.update({
        'profile_id': profile.pk,
    })
    if profile.name:
        kwargs['slug'] = profile.name
    return reverse(view, kwargs=kwargs)


@register.filter
def country(iso: str):
    try:
        countries = country._cache
    except AttributeError:
        countries = dict(django_countries.countries.countries)
        setattr(country, '_cache', countries)
    try:
        return countries[iso.upper()]
    except (AttributeError, KeyError):
        return _('Terra Incognita')


@register.simple_tag
def map_background_picture(mapname, type='background'):
    return _map_background_picture(mapname, type=type)


@lru_cache
def _map_background_picture(mapname, *, type):
    path_fmt = 'images/maps/%s/{map_slug}.jpg' % type
    map_path = path_fmt.format(map_slug=slugify(mapname))
    # default map is intro
    if not find_staticfile(map_path):
        return _intro_background_picture(type)
    return static(map_path)


@lru_cache
def _intro_background_picture(type: str) -> str:
    path = f'images/maps/{type}/intro.jpg'
    return static(path)


@register.simple_tag
def map_briefing_text(mapname):
    return _map_briefing_text(mapname)


@lru_cache
def _map_briefing_text(mapname):
    try:
        template_name = f'tracker/includes/briefing/{slugify(mapname)}.html'
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None


@register.simple_tag
def gametype_rules_text(gametype):
    return _gametype_rules_text(gametype)


@lru_cache
def _gametype_rules_text(gametype):
    try:
        template_name = f'tracker/includes/rules/{slugify(gametype)}.html'
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None
