# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_auto_20141122_1609_change_procedure_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE tracker_weapon ALTER COLUMN id TYPE bigint;",
            "ALTER TABLE tracker_weapon ALTER COLUMN id TYPE int;",
        ),
    ]
