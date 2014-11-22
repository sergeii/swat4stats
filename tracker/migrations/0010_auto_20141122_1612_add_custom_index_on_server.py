# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0009_auto_20141122_1611_add_custom_index_on_rank'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX tracker_server_host_ip_port ON tracker_server (HOST(ip), port);",
            "DROP INDEX tracker_server_host_ip_port;",
        ),
    ]
