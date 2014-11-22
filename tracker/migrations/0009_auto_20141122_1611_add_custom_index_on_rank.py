# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0008_auto_20141122_1609_change_weapon_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX tracker_rank_year_category_position_lte on tracker_rank (year, category) WHERE position <= 5;",
            "DROP INDEX tracker_rank_year_category_position_lte;",
        ),
    ]
