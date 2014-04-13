# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import re
import six

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from . import models
from .definitions import stream_pattern_node


class GameFilterForm(forms.Form):
    MAX_NAMES = 5

    GAMETYPE_CHOICES = sorted(
        # 0: _('MODE_BS')
        [(k, _('MODE_%s' % k)) for k, v in six.iteritems(stream_pattern_node.item('gametype').table)],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    GAMETYPE_CHOICES.insert(0, ('', pgettext_lazy('gamefilter', 'All game types')))

    MAP_CHOICES = sorted(
        # 0: _('A-Bomb Nightclub)
        [(k, _(v)) for k, v in six.iteritems(stream_pattern_node.item('mapname').table)],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    MAP_CHOICES.insert(0, ('', pgettext_lazy('gamefilter', 'All maps')))

    OUTCOME_CHOICES = sorted(
        # 5: _('OUTCOME_TIE')
        # remove the None type outcome
        [(k, _('OUTCOME_%s' % v.upper())) for k, v in six.iteritems(stream_pattern_node.item('outcome').table) if v != 'none'],
        # sort gametype table by the dict key
        key=lambda item: int(item[0])
    )
    OUTCOME_CHOICES.insert(0, ('', pgettext_lazy('gamefilter', 'All results')))

    GAMETIME_CHOICES = [
        (x, pgettext_lazy('gamefilter', '%(min)s+ minutes') % {'min': x}) for x in range(0, 31, 5)
    ]

    server = forms.ModelChoiceField(
        label=pgettext_lazy('gamefilter', 'Server'),
        required=False, 
        queryset=models.Server.objects.all(), 
        empty_label=_('All servers')
    )
    gametype = forms.ChoiceField(
        label=pgettext_lazy('gamefilter', 'Game Type'),
        required=False, 
        choices=GAMETYPE_CHOICES
    )
    map = forms.ChoiceField(
        label=pgettext_lazy('gamefilter', 'Map'),
        required=False, 
        choices=MAP_CHOICES
    )
    outcome = forms.ChoiceField(
        label=pgettext_lazy('gamefilter', 'Game Result'),
        required=False, 
        choices=OUTCOME_CHOICES
    )
    gametime = forms.TypedChoiceField(
        label=pgettext_lazy('gamefilter', 'Game Time'),
        required=False, 
        choices=GAMETIME_CHOICES,
        coerce=int
    )
    players = forms.CharField(
        min_length=3,
        label=pgettext_lazy('gamefilter', 'Participated Players'),
        required=False
    )

    def clean_players(self, *args, **kwargs):
        data = self.cleaned_data.get('players', '')
        names = list(filter(None, map(str.strip, re.split(r'[\s,]+', data))))
        # limit number of player names with MAX_NAMES
        if len(names) > self.MAX_NAMES:
            raise ValidationError(
                _('Too many names specified.'), 
                params={'max': self.MAX_NAMES}
            )
        return names
