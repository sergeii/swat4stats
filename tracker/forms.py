# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import re
import six

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone, dates
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import truncatechars

from . import models
from .definitions import stream_pattern_node
from .utils import force_clean_name


class FilterFormMixin(object):
    filter_fields = ()

    def clean(self):
        cleaned_data = super(FilterFormMixin, self).clean()
        # if unchecked, remove the corresponding select choices
        for field in self.filter_fields:
            if isinstance(field, (list, tuple)):
                field, sentinel = field
            else:
                sentinel = field
            # if not checked, ensure the field value is not present
            if not cleaned_data.get('filter_%s' % sentinel, None):
                try:
                    del cleaned_data[field]
                except KeyError:
                    pass
        return cleaned_data


class ServerChoiceField(forms.ModelChoiceField):
    MAX_NAME_CHARS = 30

    def label_from_instance(self, obj):
        return truncatechars(force_clean_name(obj.name), self.MAX_NAME_CHARS)


class GameFilterForm(FilterFormMixin, forms.Form):
    filter_fields = (
        'gametype', 
        'mapname', 
        'outcome', 
        'server', 
        'players', 
        ('year', 'date'),
        ('month', 'date'),
        ('day', 'date'),
    )

    MAX_NAMES = 5
    MIN_YEAR = 2007

    GAMETYPE_CHOICES = sorted(
        # 0: _('MODE_BS')
        [(k, _(v)) for k, v in six.iteritems(stream_pattern_node.item('gametype').table)],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    MAP_CHOICES = sorted(
        # 0: _('A-Bomb Nightclub)
        [(k, _(v)) for k, v in six.iteritems(stream_pattern_node.item('mapname').table)],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    OUTCOME_CHOICES = sorted(
        # 5: _('OUTCOME_TIE')
        # remove the None type outcome
        [(k, _('OUTCOME_LONG_%s' % k)) for k, v in six.iteritems(stream_pattern_node.item('outcome').table) if v != 'none'],
        # sort gametype table by the dict key, tie goes first
        key=lambda item: (item[0] != '5', int(item[0]))
    )
    # 0, 5, 10,.. 30
    GAMETIME_CHOICES = [
        (x, _('%(min)s+ minutes') % {'min': x}) for x in range(0, 31, 5)
    ]

    year = forms.ChoiceField(
        label=_('Year'),
        required=False,
        choices=[('', _('Any'))] + [(year, year) for year in range(timezone.now().year, MIN_YEAR-1, -1)]
    )
    month = forms.ChoiceField(
        label=_('Month'),
        required=False,
        choices=[('', _('Any'))] + list(dates.MONTHS.items()),
    )
    day = forms.ChoiceField(
        label=_('Day'),
        required=False,
        choices=[('', _('Any'))] + [(day, day) for day in range(1, 32)],
    )
    server = ServerChoiceField(
        label=_('Server'),
        required=False, 
        queryset=models.Server.objects.streamed(),
        empty_label=_('Any')
    )
    gametype = forms.ChoiceField(
        label=_('Game Type'),
        required=False, 
        choices=GAMETYPE_CHOICES
    )
    mapname = forms.ChoiceField(
        label=_('Map'),
        required=False, 
        choices=MAP_CHOICES
    )
    outcome = forms.ChoiceField(
        label=_('Result'),
        required=False, 
        choices=OUTCOME_CHOICES
    )
    gametime = forms.TypedChoiceField(
        label=_('Round Time'),
        required=False, 
        choices=GAMETIME_CHOICES,
        coerce=int
    )
    players = forms.CharField(
        min_length=5,
        max_length=128,
        label=_('Participated Players'),
        required=False,
    )

    filter_gametype = forms.BooleanField(required=False)
    filter_mapname = forms.BooleanField(required=False)
    filter_outcome = forms.BooleanField(required=False)
    filter_date = forms.BooleanField(required=False)
    filter_server = forms.BooleanField(required=False)
    filter_players = forms.BooleanField(required=False)

    def clean_players(self, *args, **kwargs):
        """
        Ensure the players field does not contain more than `MAX_NAMES` entries.
        """
        data = self.cleaned_data.get('players', '')
        names = list(filter(None, map(str.strip, re.split(r'[\s,]+', data))))
        # limit number of player names with MAX_NAMES
        if len(names) > self.MAX_NAMES:
            raise ValidationError(
                _('Too many names specified.'), 
                params={'max': self.MAX_NAMES}
            )
        return names


class ServerFilterForm(FilterFormMixin, forms.Form):
    filter_fields = (
        'gamename', 
        'gametype', 
        'gamever', 
    )

    # reuse gametype choices from the game filter form
    GAMETYPE_CHOICES = GameFilterForm.GAMETYPE_CHOICES
    GAMENAME_CHOICES = sorted(
        # 0: _('MODE_BS')
        [(k, _(v)) for k, v in six.iteritems(stream_pattern_node.item('gamename').table)],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    GAMEVER_CHOICES = (('1.0', '1.0'), ('1.1', '1.1'),)

    # game label filter
    gamename = forms.ChoiceField(label=_('Game Label'), choices=GAMENAME_CHOICES, required=False)
    gametype = forms.ChoiceField(label=_('Game Type'), choices=GAMETYPE_CHOICES, required=False)
    gamever = forms.ChoiceField(label=_('Game Version'), choices=GAMEVER_CHOICES, required=False)

    filter_gamename = forms.BooleanField(required=False)
    filter_gamever = forms.BooleanField(required=False)
    filter_gametype = forms.BooleanField(required=False)

    filter_empty = forms.BooleanField(label=_('Hide Empty Servers'), required=False)
    filter_full = forms.BooleanField(label=_('Hide Full Servers'), required=False)
    filter_passworded = forms.BooleanField(label=_('Hide Password Protected'), required=False)


class PlayerSearchForm(forms.Form):

    player = forms.CharField(
        min_length=3,
        max_length=64,
        label=_('Player Name'),
        required=True
    )
