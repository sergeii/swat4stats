# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import datetime
import six

from django import template
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.text import slugify
from django.utils.translation import override, ungettext_lazy, ugettext as _
from django.utils import timesince, timezone
from julia import shortcuts

from tracker import definitions, utils

register = template.Library()


@register.filter
def times(number, step=1):
    return six.moves.xrange(0, number, step)


@register.filter
def accuracy(number):
    return int(number * 100)


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


@register.inclusion_tag('tracker/tags/show_player.html')
def show_player(player):
    return locals()


@register.inclusion_tag('tracker/tags/show_player_picture.html')
def show_player_picture(player):
    return locals()


@register.inclusion_tag('tracker/tags/show_country.html')
def show_country(country):
    return locals()


@register.simple_tag
def game_url(game, view='tracker:game_detail', **kwargs):
    kwargs.update({
        'game_id': game.pk,
        'slug': '/'.join([
            game.date_finished.strftime('%Y'), 
            game.date_finished.strftime('%m'), 
            game.date_finished.strftime('%d'),
            slugify(shortcuts.map(definitions.stream_pattern_node, 'mapname', force_text(game.mapname))),
        ])
    })
    return reverse(view, kwargs=kwargs)


@register.simple_tag
def server_url(server, **kwargs):
    kwargs.update({
        'server_ip': server.ip,
        'server_port': server.port,
    })
    return reverse('tracker:server_detail', kwargs=kwargs)


@register.simple_tag
def profile_url(profile, view='tracker:profile_detail', **kwargs):
    return utils.get_profile_url(profile, view, **kwargs)


@register.inclusion_tag('tracker/tags/show_profile_picture.html')
def show_profile_picture(profile, *args):
    return {
        'profile': profile,
        'noflag': ('noflag' in args),
    }


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
def gametype(gametype):
    return _('MODE_%s' % gametype)


@register.filter
def gametype_short(gametype):
    return _('MODE_SHORT_%s' % gametype)


@register.filter
def mapname(mapname):
    return _(shortcuts.map(definitions.stream_pattern_node, 'mapname', force_text(mapname)))


@register.filter
def weapon(weapon):
    return _(shortcuts.map(definitions.stream_pattern_node.item('players').item, 'loadout__primary', force_text(weapon)))


@register.filter
def procedure(procedure):
    return _('PROCEDURE_%s' % procedure)


@register.filter
def objective(objective):
    return _('OBJECTIVE_%s' % objective)


@register.filter
def objective_status(status):
    return _('OBJECTIVE_STATUS_%s' % status)


@register.filter
def coop_status(status):
    return _('COOP_STATUS_%s' % status)


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
    import django_countries
    iso = iso.upper()
    countries = dict(django_countries.countries)
    return dict(countries)[iso] if iso in countries else ''


@register.simple_tag
def zerohero(value, best_value, class_best, class_zero):
    if not value:
        return class_zero
    if value >= best_value:
        return class_best
    return ''