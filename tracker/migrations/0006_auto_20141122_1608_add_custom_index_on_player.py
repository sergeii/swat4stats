# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_auto_20141122_1607_change_objective_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX tracker_player_host_ip_id_desc ON tracker_player (HOST(ip), id DESC);",
            "DROP INDEX tracker_player_host_ip_id_desc;",
        ),
    ]
