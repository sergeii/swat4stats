# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_auto_20141122_1551_add_upper_name_index_on_alias'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE INDEX tracker_game_date_finished_desc ON tracker_game (date_finished DESC);
            CREATE INDEX tracker_game_score_swat_score_sus ON tracker_game ((score_swat+score_sus) DESC);
            """,
            """
            DROP INDEX tracker_game_date_finished_desc;
            DROP INDEX tracker_game_score_swat_score_sus;
            """,
        ),
    ]
