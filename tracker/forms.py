from django import forms
from django.utils.translation import gettext_lazy as _


class PlayerSearchForm(forms.Form):
    player = forms.CharField(
        min_length=3,
        max_length=64,
        label=_('Player Name'),
        required=True
    )
