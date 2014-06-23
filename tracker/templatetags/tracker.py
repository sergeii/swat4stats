# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import re
import datetime
import json
from functools import partial
import importlib
import math

import six

from django import template
from django.core.urlresolvers import reverse, resolve
from django.utils.encoding import force_text
from django.utils import html
from django.utils.text import slugify
from django.utils.translation import override, pgettext, ungettext_lazy, ugettext as _
from django.utils import timesince, timezone
from django.contrib.humanize.templatetags import humanize
from django.template import defaultfilters

from julia import shortcuts
from julia.node import BaseNodeError
import django_countries

from tracker import definitions, utils

register = template.Library()
trans = _


@register.filter
def highlight(text, word):
    word = re.escape(html.escape(word))
    text = html.escape(text)
    return html.mark_safe(re.sub(r'(%s)' % word, r'<span class="highlight">\1</span>', text, flags=re.I))


@register.filter
def times(number, step=1):
    return six.moves.xrange(0, number, step)


@register.filter
def tojson(obj):
    return json.dumps(obj)


@register.filter
@register.simple_tag
def ratio(divident, divisor, places=2):
    try:
        return round(divident/divisor, 2)
    except:
        return 0


@register.filter
def percent(number):
    return '{0}%'.format(int(number * 100))


@register.inclusion_tag('tracker/tags/show_game.html')
def show_game(game, *desc, **kwargs):
    simple = kwargs.pop('simple', False)
    context = {
        'game': game,
        'desc': ' '.join(desc),
        'simple': simple,
    }
    if not simple:
        context.update({
            'score_readable': '%d/100' % game.coop_score_normal if game.coop_game else '%d:%d' % (game.score_swat, game.score_sus),
        })
    return context


@register.inclusion_tag('tracker/tags/show_game_light.html')
def show_game_light(game):
    return locals()


@register.inclusion_tag('tracker/tags/show_game_picture_light.html')
def show_game_picture_light(game):
    return locals()


@register.inclusion_tag('tracker/tags/show_player.html')
def show_player(player):
    return locals()


@register.inclusion_tag('tracker/tags/show_player_picture.html')
def show_player_picture(player, size=None):
    return locals()


@register.inclusion_tag('tracker/tags/show_country.html')
def show_country(country):
    return locals()


@register.simple_tag
def game_url(game, view='tracker:game', **kwargs):
    kwargs.update({
        'game_id': game.pk,
    })
    try:
        kwargs.update({
            'slug_year': game.date_finished.strftime('%Y'), 
            'slug_month': game.date_finished.strftime('%m'), 
            'slug_day': game.date_finished.strftime('%d'),
            'slug_name': slugify(shortcuts.map(definitions.stream_pattern_node, 'mapname', force_text(game.mapname))),
        })
    except BaseNodeError:
        pass
    return reverse(view, kwargs=kwargs)


@register.simple_tag
def server_url(server, view='tracker:server', **kwargs):
    kwargs.update({
        'server_ip': server.ip,
        'server_port': server.port,
    })
    return reverse(view, kwargs=kwargs)


@register.simple_tag
def profile_url(profile, view='tracker:profile_overview', **kwargs):
    kwargs.update({
        'profile_id': profile.pk,
    })
    if profile.name:
        kwargs['slug'] = profile.name
    if 'year' in kwargs and not kwargs['year']:
        del kwargs['year']
    return reverse(view, kwargs=kwargs)


@register.inclusion_tag('tracker/tags/show_profile_picture.html')
def show_profile_picture(profile, size=None, *args, **kwargs):
    kwargs.update({
        'profile': profile,
        'noflag': ('noflag' in args),
        'size': size,
    })
    return kwargs


@register.inclusion_tag('tracker/tags/show_weapon_picture.html')
def show_weapon_picture(name):
    return locals()


@register.inclusion_tag('tracker/tags/show_loadout_picture.html')
def show_loadout_picture(loadout, slot, *args):
    return dict(locals(), **{
        'item': getattr(loadout, slot),
        'nocaption': 'nocaption' in args,
    })


@register.filter
def gamename(gamename):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'gamename', force_text(gamename)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def gametype(gametype):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'gametype', force_text(gametype)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def gametype_short(gametype):
    return trans('MODE_SHORT_%s' % gametype)


@register.filter
def outcome(outcome):
    return html.mark_safe(trans('OUTCOME_%s' % outcome))


@register.filter
def mapname(mapname):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'mapname', force_text(mapname)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def weapon(weapon):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node.item('players').item, 'loadout__primary', force_text(weapon)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def procedure(procedure):
    return trans('PROCEDURE_%s' % procedure)


@register.filter
def objective(objective):
    return trans('OBJECTIVE_%s' % objective)


@register.filter
def objective_status(status):
    return trans('OBJECTIVE_STATUS_%s' % status)


@register.filter
def coop_status(status):
    return trans('COOP_STATUS_%s' % status)


@register.filter
def statname(statid):
    return definitions.STATS[statid]


@register.filter
def colorless(string):
    return utils.force_clean_name(string)


@register.filter
def swattime(seconds):
    seconds = int(seconds or 0)
    items = (86400, 3600, 60, 1)
    time = []
    # > 0
    for value in items:
        unit = int(seconds // value)
        if unit > 0:
            seconds -= unit*value
            unit = force_text(unit)
            time.append(unit)
        elif time:
            time.append('0')
    # prepend zero minutes, zero seconds
    while len(time) < 2:
        time.insert(0, '0')
    # leave the leading unit without a leading zero
    return ':'.join(map(lambda t: t[1].rjust(2, '0') if t[0] else t[1], enumerate(time)))


@register.filter
def humantime(seconds):
    now = timezone.now()
    return timesince.timesince(now - datetime.timedelta(seconds=seconds or 0), now).split(',')[0].strip()


@register.filter
def hours(seconds):
    return int(seconds) // (60*60)


@register.filter
def humanhours(seconds):
    return ungettext_lazy('%d hour', '%d hours') % hours(seconds)


@register.filter
def country(iso):
    try:
        countries = country.dict
    except AttributeError:
        countries = dict(django_countries.countries)
        setattr(country, 'dict', countries)
    try:
        return countries[iso.upper()]
    except:
        return _('Terra Incognita')


@register.simple_tag
def zerohero(value, best_value, class_best, class_zero):
    if not value:
        return class_zero
    if value >= best_value:
        return class_best
    return ''


@register.filter
def valueformat(value, format):
    return {
        'hours': humanhours,
        'time': humantime,
        'int': lambda value: humanize.intcomma(int(value)),
        'ordinal': humanize.ordinal,
        'ratio': lambda value: defaultfilters.floatformat(value, 2),
        'percent': percent,
    # return the value as if the specified format is not present
    }.get(format, lambda value: value)(value)


@register.filter
def clean_name(value):
    return utils.force_clean_name(value)


@register.filter
def format_name(value):
    return utils.format_name(value)


# credits: http://stackoverflow.com/questions/5749075/django-get-generic-view-class-from-url-name
@register.assignment_tag
def page_url(view, number, *args, **kwargs):
    """
    Attempt to reverse url for given view and append a querystring param 'page' to the url.

    The view name must point to a class based view with the class attributes paginate_by and page_kwarg.
    """
    url = reverse(view, args=args, kwargs=kwargs)
    func = resolve(url).func
    # import the module
    cls = getattr(importlib.import_module(func.__module__), func.__name__)
    try:
        page = int(math.ceil(number / cls.paginate_by))
    except:
        return url
    return '%s?%s=%s' % (url, cls.page_kwarg, page)
