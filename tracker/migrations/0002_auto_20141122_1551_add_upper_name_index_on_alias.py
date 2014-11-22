# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX tracker_alias_upper_name_isp_id ON tracker_alias (upper(name), isp_id);",
            "DROP INDEX tracker_alias_upper_name_isp_id;",
        ),
    ]
