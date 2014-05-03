# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from django.contrib import admin

from . import models


admin.site.register(models.Round)
admin.site.register(models.RoundPlayer)
admin.site.register(models.Player)