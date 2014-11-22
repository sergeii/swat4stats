# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_auto_20141122_1608_add_custom_index_on_player'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE tracker_procedure ALTER COLUMN id TYPE bigint;",
            "ALTER TABLE tracker_procedure ALTER COLUMN id TYPE int;",
        ),
    ]
