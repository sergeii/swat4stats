# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_auto_20141122_1558_add_functional_index_on_game'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX tracker_ip_length ON tracker_ip ((range_to - range_from));",
            "DROP INDEX tracker_ip_length;",
        ),
    ]
