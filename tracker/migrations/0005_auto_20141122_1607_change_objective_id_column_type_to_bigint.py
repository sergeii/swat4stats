# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_auto_20141122_1601_add_ip_length_index'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE tracker_objective ALTER COLUMN id TYPE bigint;",
            "ALTER TABLE tracker_objective ALTER COLUMN id TYPE int;",
        ),
    ]
