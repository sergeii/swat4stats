# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='IP',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('range_from', models.BigIntegerField()),
                ('range_to', models.BigIntegerField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'tracker_ip',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ISP',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255, null=True)),
                ('country', models.CharField(max_length=2, null=True)),
            ],
            options={
                'db_table': 'tracker_isp',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='ip',
            name='isp',
            field=models.ForeignKey(to='geoip.ISP', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='ip',
            unique_together=set([('range_from', 'range_to')]),
        ),
    ]
