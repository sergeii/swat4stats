from functools import partial

from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.translation import ngettext, gettext_lazy as _


def format_ratio(value):
    return round(value, 1)


def format_ratio_percent(value):
    return _('%(value)s%%') % {'value': round(value * 100)}


def format_number(singular, plural, number):
    number = int(number)
    return ngettext(singular, plural, number) % {'number': intcomma(number)}


format_score = partial(format_number, '%(number)s point', '%(number)s points')
format_seconds = partial(format_number, '%(number)s second', '%(number)s seconds')
format_kills = partial(format_number, '%(number)s kill', '%(number)s kills')
format_arrests = partial(format_number, '%(number)s arrest', '%(number)s arrests')
format_rescues = partial(format_number, '%(number)s rescue', '%(number)s rescues')
format_missions = partial(format_number, '%(number)s mission', '%(number)s missions')
