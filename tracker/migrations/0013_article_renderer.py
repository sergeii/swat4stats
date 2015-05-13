# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0012_server_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='renderer',
            field=models.SmallIntegerField(choices=[(1, 'Plain text'), (2, 'HTML'), (3, 'Markdown')], default=3),
        ),
    ]
