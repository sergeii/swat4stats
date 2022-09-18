import re
import datetime
import json
import math

from django import template
from django.urls import reverse, resolve
from django.utils import html
from django.utils.text import slugify
from django.utils.translation import ngettext_lazy, gettext as _
from django.utils import timesince, timezone
from django.contrib.humanize.templatetags import humanize
from django.template import defaultfilters
import django_countries

from vendor.julia import shortcuts
from vendor.julia.node import BaseNodeError
from tracker import definitions

register = template.Library()
trans = _


@register.filter
def highlight(text, word):
    word = re.escape(html.escape(word))
    text = html.escape(text)
    return html.mark_safe(re.sub(r'(%s)' % word, r'<span class="highlight">\1</span>', text, flags=re.I))


@register.filter
def tojson(obj):
    return json.dumps(obj)


@register.filter
@register.simple_tag
def ratio(divident, divisor, places=2):
    try:
        return round(divident/divisor, 2)
    except ZeroDivisionError:
        return 0


@register.filter
def percent(number):
    return f'{int(number * 100)}%'


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
            'score_readable': (f'{game.coop_score_normal}/100'
                               if game.coop_game
                               else f'{game.score_swat}:{game.score_sus}')
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
            'year': game.date_finished.strftime('%Y'),
            'month': game.date_finished.strftime('%m'),
            'day': game.date_finished.strftime('%d'),
            'slug': slugify(shortcuts.map(definitions.stream_pattern_node, 'mapname', str(game.mapname))),
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


@register.inclusion_tag('tracker/tags/show_loadout_picture.html')
def show_loadout_picture(loadout, slot, *args):
    return dict(locals(), **{
        'item': getattr(loadout, slot),
        'nocaption': 'nocaption' in args,
    })


@register.filter
def gamename(gamename):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'gamename', str(gamename)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def gametype(gametype):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'gametype', str(gametype)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def gametype_short(gametype):
    return trans(f'MODE_SHORT_{gametype}')


@register.filter
def outcome(outcome):
    return html.mark_safe(trans(f'OUTCOME_{outcome}'))


@register.filter
def mapname(mapname):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node, 'mapname', str(mapname)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def weapon(weapon):
    try:
        return _(shortcuts.map(definitions.stream_pattern_node.item('players').item, 'loadout__primary', str(weapon)))
    except BaseNodeError:
        return _('Unknown')


@register.filter
def procedure(procedure):
    return trans(f'PROCEDURE_{procedure}')


@register.filter
def objective(objective):
    return trans(f'OBJECTIVE_{objective}')


@register.filter
def objective_status(status):
    return trans(f'OBJECTIVE_STATUS_{status}')


@register.filter
def coop_status(status):
    return trans(f'COOP_STATUS_{status}')


@register.filter
def statname(statid):
    return definitions.STATS[statid]


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
            unit = str(unit)
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
    return ngettext_lazy('%d hour', '%d hours') % hours(seconds)


@register.filter
def country(iso):
    try:
        countries = country.dict
    except AttributeError:
        countries = dict(django_countries.countries.countries)
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
        'int': lambda v: humanize.intcomma(int(v)),
        'ordinal': humanize.ordinal,
        'ratio': lambda v: defaultfilters.floatformat(v, 2),
        'percent': percent,
        # return the value as if the specified format is not present
    }.get(format, lambda value: value)(value)


# credits: http://stackoverflow.com/questions/5749075/django-get-generic-view-class-from-url-name
@register.simple_tag
def page_url(view, number, *args, **kwargs):
    """
    Attempt to reverse url for given view and append a querystring param 'page' to the url.

    The view name must point to a class based view with the class attributes paginate_by and page_kwarg.
    """
    url = reverse(view, args=args, kwargs=kwargs)
    cls = resolve(url).func.view_class
    try:
        page = int(math.ceil(number / cls.paginate_by))
    except (ValueError, TypeError, ZeroDivisionError):
        return url
    return f'{url}?{cls.page_kwarg}={page}'
