# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0011_server_pinned'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='version',
            field=models.CharField(max_length=64, blank=True, null=True),
            preserve_default=True,
        ),
    ]
